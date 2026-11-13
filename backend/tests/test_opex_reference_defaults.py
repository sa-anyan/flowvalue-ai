"""OPEX reference defaults: cited, in range, never overwriting, AI-free."""

from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

import openpyxl
import pytest

from backend.opex import reference_library
from backend.opex.indexes.garrett.model import CATEGORIES, SOURCE
from backend.opex.models import Basis
from backend.opex.reference_defaults import propose
from backend.blocks.opex.input_builder import _costs_for_year, _opex


def _report():
    from backend.orchestration.ingest import parse

    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Balance"
    sheet.append(["Stream ID", "Description", "Mass flow (kg/h)", "Temperature (C)", "Pressure (bar)"])
    sheet.append(["S-1", "Water feed to Electrolyser EL-1", 900, 25, 1])
    sheet.append(["S-2", "Dry H2 from Electrolyser EL-1", 100, 60, 30])
    sheet.append(["S-3", "Dry O2 from Electrolyser EL-1", 800, 60, 1])
    data = BytesIO()
    book.save(data)
    return parse(data.getvalue(), "pem.xlsx")["report"]


BASE_CONFIG = {
    "price_basis": {"currency": "USD", "price_period": "2026-09"},
    "assumption_date": "2026-11-13",
    "operating": {"days_per_year": 330, "hours_per_day": 24, "rationale": "test"},
}
SPECIFIC_ENERGY = [{"id": "Basis!C9", "parameter": "Electricity per hydrogen", "value": 55.5, "unit": "kWh/kg H2"}]


def test_every_garrett_category_gets_a_cited_default_inside_its_range():
    config, summary = propose({}, {"entities": [], "connections": []})
    factors = config["garrett_factors"]
    with_base = [c for c in CATEGORIES if c.base]
    assert set(factors) == {c.id for c in with_base}
    for c in with_base:
        choice = factors[c.id]
        assert Decimal(c.minimum) <= Decimal(str(choice["fraction"])) <= Decimal(c.maximum)
        assert choice["source"] == SOURCE.reference and "p.52" in choice["page"] and "Table 4-4" in choice["page"]
        assert choice["origin"] == "reference_default" and choice["value_basis"] == "midpoint"
        assert choice["rationale"].startswith("Reference default: " + SOURCE.reference)
    assert factors["maintenance"]["fraction"] == pytest.approx(0.06)  # midpoint of .02–.10


def test_user_ai_and_override_values_are_never_replaced():
    existing = {
        "garrett_factors": {"maintenance": {"fraction": 0.09, "rationale": "User-selected factor"},
                            "research_development": {"fraction": 0.05, "override": True, "override_reason": "documented"}},
        "energy": [{"id": "ai-power", "name": "AI electricity"}],
        "materials": [{"id": "user-feed", "name": "User feed"}],
    }
    config, _ = propose(existing, _report(), design_basis_rows=SPECIFIC_ENERGY)
    assert config["garrett_factors"]["maintenance"] == existing["garrett_factors"]["maintenance"]
    assert config["garrett_factors"]["research_development"] == existing["garrett_factors"]["research_development"]
    assert config["energy"] == existing["energy"] and config["materials"] == existing["materials"]
    assert "garrett_factors.maintenance" not in config["value_owners"]


def test_utilities_come_from_the_design_value_times_hours_and_missing_tariff_is_a_question():
    report = _report()
    config, summary = propose(dict(BASE_CONFIG), report, design_basis_rows=SPECIFIC_ENERGY)
    energy = config["energy"]
    assert len(energy) == 1 and energy[0]["method"] == "specific_energy" and energy[0]["specific_kwh_per_kg"] == 55.5
    assert energy[0]["tariff_per_kwh"] is None
    assert any("tariff" in q["question"].lower() for q in summary["questions"])
    basis = Basis("USD", "2026-09")
    _, detail = _costs_for_year(report, config, basis, Decimal(330 * 24), Decimal(1), 1, partial=True)
    reasons = " ".join(p["reason"] for p in detail["pending_items"])
    expected = 100 * 55.5 * 330 * 24  # kg/h × kWh/kg × h/year
    assert f"{expected:,.0f} kWh/year" in reasons and "tariff needed" in reasons
    # With a tariff from the workbook, the item is priced.
    priced, _ = propose(dict(BASE_CONFIG), report, design_basis_rows=SPECIFIC_ENERGY,
                        workbook_params=[{"id": "Basis!C10", "label": "Electricity price", "value": 0.08, "unit": "USD/kWh"}])
    costs, detail = _costs_for_year(report, priced, basis, Decimal(330 * 24), Decimal(1), 1, partial=True)
    line = next(c for c in costs if c.category == "utilities")
    assert float(line.quantity) == pytest.approx(expected) and float(line.rate) == pytest.approx(0.08)


def test_feed_streams_are_proposed_with_quantity_and_a_price_question():
    report = _report()
    config, summary = propose(dict(BASE_CONFIG), report)
    feeds = config.get("materials") or []
    # Feeds are streams entering a unit with no source unit; products are not feeds.
    assert all("H2" not in f["name"] and "O2" not in f["name"] for f in feeds)
    for feed in feeds:
        assert feed["unit_price"] is None and any(feed["id"] == q["id"] for q in summary["questions"])


def test_pending_source_rows_are_never_used(monkeypatch):
    slot = {"category": "maintenance", "base": "x", "low": "0.5", "typical": "0.6", "high": "0.9",
            "units": "", "source": "Turton", "page": None, "applicability": "", "status": "pending_source_check"}
    monkeypatch.setattr(reference_library.turton, "ROWS", (slot,))
    assert reference_library.get_ranges("maintenance", "turton") == []
    assert reference_library.get_correlation("operating_labor", "turton") is None
    assert slot in [{k: v for k, v in r.items() if k != "method"} for r in reference_library.pending_slots()]
    config, summary = propose({}, {"entities": [], "connections": []})
    assert config["garrett_factors"]["maintenance"]["fraction"] == pytest.approx(0.06)  # Garrett, not the slot
    assert any(q["id"] == "operating_labor" for q in summary["questions"])


def test_ai_off_opex_is_complete_except_genuine_price_questions():
    report = _report()
    config, _ = propose(dict(BASE_CONFIG), report, design_basis_rows=SPECIFIC_ENERGY,
                        workbook_params=[{"id": "Basis!C10", "label": "Electricity price", "value": 0.08, "unit": "USD/kWh"}])
    basis = Basis("USD", "2026-09")
    hours = Decimal(330 * 24)
    _, detail = _costs_for_year(report, config, basis, hours, Decimal(1), 1, partial=True)
    reasons = [p["reason"] for p in detail["pending_items"]]
    assert all(r.startswith("Price needed") or "operating_labor" in r for r in reasons), reasons
    # The user answers the genuine questions: feed prices and operating labour.
    for feed in config.get("materials") or []:
        feed["unit_price"] = 0.002
    config["labour"] = [{"id": "ops", "role": "Operators", "category": "operating_labor", "behavior": "fixed",
                         "headcount_fte": 5, "annual_base_salary": 60000, "allocation_fraction": 1,
                         "rationale": "user", "uncertainty": "user"}]
    costs, detail = _costs_for_year(report, config, basis, hours, Decimal(1), 1, partial=True)
    assert detail["pending_items"] == []
    capex = SimpleNamespace(fixed_capital=Decimal("10000000"), purchased_equipment=Decimal("3000000"),
                            startup_expenses=Decimal("500000"))
    result = _opex(capex, basis, costs, Decimal("5000000"), allow_partial=True)
    assert result.annual_cash_opex is not None and result.annual_cash_opex > 0


def test_air_and_water_to_be_treated_are_not_proposed_as_purchased_feeds():
    from backend.orchestration.ingest import parse

    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Balance"
    sheet.append(["Stream ID", "Description", "Mass flow (kg/h)", "Temperature (C)", "Pressure (bar)"])
    sheet.append(["3", "Wastewater Influent to Buffer Tank B-001", 125000, 20, 1])
    sheet.append(["10", "Pressurised Sterile Air to Bioreactor R-001", 74, 25, 2])
    sheet.append(["6", "Sucrose from Supplier to Bioreactor R-001", 66, 25, 1])
    sheet.append(["4", "Treated water from Bioreactor R-001", 125000, 25, 1])
    data = BytesIO()
    book.save(data)
    report = parse(data.getvalue(), "plant.xlsx")["report"]
    config, summary = propose(dict(BASE_CONFIG), report)
    names = [f["name"] for f in config.get("materials") or []]
    assert any("Sucrose" in n for n in names)
    assert not any("Wastewater" in n or "Air" in n for n in names)
    skipped = " ".join(n["name"] for n in config["reference_defaults"]["not_costed"])
    assert "Wastewater" in skipped and "Air" in skipped


def test_pending_price_items_carry_their_yearly_quantity():
    report = _report()
    config, _ = propose(dict(BASE_CONFIG), report, design_basis_rows=SPECIFIC_ENERGY)
    basis = Basis("USD", "2026-09")
    _, detail = _costs_for_year(report, config, basis, Decimal(330 * 24), Decimal(1), 1, partial=True)
    energy = next(p for p in detail["pending_items"] if p["group"] == "energy")
    assert energy["unit"] == "kWh" and energy["annual_quantity"] == pytest.approx(100 * 55.5 * 330 * 24)
