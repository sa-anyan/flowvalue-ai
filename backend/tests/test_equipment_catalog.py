import json
from importlib.resources import files

from fastapi.testclient import TestClient

from app.engine.equipment_catalog import catalog, match_report
from app.main import app
from app.parsers.balance.models import BalanceReport, Entity, Evidence


def report(text, tag="P-001", prop="description"):
    evidence = Evidence(
        id="v1",
        workbook="test.xlsx",
        sheet="Balance",
        cell="B2",
        property=prop,
        label=prop,
        original_value=text,
    )
    unit = Entity(
        key="unit",
        kind="equipment",
        identifier=tag,
        table="table",
        id_evidence=Evidence(
            id="id",
            workbook="test.xlsx",
            sheet="Balance",
            cell="A2",
            property="identifier",
            label="Tag",
            original_value=tag,
        ),
        values=[evidence],
    )
    return BalanceReport(
        filename="test.xlsx", sha256="0" * 64, sheets=[], entities=[unit]
    )


def match(text, tag="P-001", prop="description"):
    return match_report(report(text, tag, prop))["results"][0]


def test_seed_database_reconcile_all_appendix_pages():
    data = catalog()
    seed = json.loads(files("app.data").joinpath("equipment_catalog.json").read_text())
    assert len(data["equipment"]) == 51
    assert {row["pdf_page"] for row in data["equipment"]} == set(range(6, 57))
    assert data["source"]["sha256"] == seed["source"]["sha256"]
    assert [
        {**row, "aliases": sorted(row["aliases"])} for row in data["equipment"]
    ] == [{**row, "aliases": sorted(row["aliases"])} for row in seed["equipment"]]
    assert all(
        row["cost_method_status"] == "not_digitized" for row in data["equipment"]
    )


def test_aliases_and_plural_punctuation():
    result = match("Centrifugal Pumps P-001")
    assert result["status"] == "match"
    assert result["candidates"][0]["name"] == "Centrifugal pumps"
    assert result["evidence"][0]["cell"] == "B2"
    assert match("shell-and-tube heat exchanger E-101", "E-101")["status"] == "match"
    assert match("P-001: centrifugal pump")["status"] == "match"


def test_tag_prefix_is_not_type_and_upstream_units_not_borrowed():
    assert (
        match("Wastewater from Storage Tank T-001 to pH Adjustment Unit P-001")[
            "status"
        ]
        == "no_match"
    )
    assert match("P-001")["status"] == "no_match"
    assert match("unknown quantum separator P-001")["status"] == "no_match"
    assert match("not a centrifugal pump", prop="type")["status"] == "no_match"


def test_family_and_conflicts_require_review():
    assert match("Pump P-001")["status"] == "review"
    assert len(match("Pump P-001")["candidates"]) == 2
    assert match("Bioreactor R-001", "R-001")["status"] == "review"
    result = match(
        "Treated wastewater from Bioreactor to Biomass Settler S-001",
        "S-001",
        prop="type",
    )
    assert [x["name"] for x in result["candidates"]] == ["Thickeners and clarifiers"]
    assert match("Gear pump or centrifugal pump", prop="type")["status"] == "review"
    assert match("small tank T-001", "T-001")["candidates"][0]["name"] == "Small tanks"
    assert len(match("waste heat boiler B-001", "B-001")["candidates"]) == 1


def test_shared_references_and_scoped_keys_preserved_without_mutation():
    payload = report("ignored")
    stream = payload.entities[0].model_copy(deep=True)
    stream.kind, stream.key, stream.identifier = "material", "stream", "1"
    stream.values[0].original_value = "Centrifugal pump P-001 to Bioreactor R-001"
    payload.entities[0].values = []
    payload.entities[0].stream_keys = ["stream"]
    payload.entities.append(stream)
    before = payload.model_dump_json()
    result = match_report(payload)["results"][0]
    assert result["status"] == "match"
    assert result["equipment_key"] == "unit"
    assert payload.model_dump_json() == before


def test_api_empty_and_malformed():
    client = TestClient(app)
    assert len(client.get("/api/equipment/catalog").json()["equipment"]) == 51
    empty = BalanceReport(filename="empty.xlsx", sha256="0" * 64, sheets=[])
    assert (
        client.post("/api/equipment/match", json=empty.model_dump()).json()["results"]
        == []
    )
    assert client.post("/api/equipment/match", json={}).status_code == 422


def test_team8_catalog_matches_do_not_confuse_ph_adjustment_or_bioreactor():
    from pathlib import Path

    from app.parsers.workbook_pipeline import parse_workbook

    path = Path(__file__).parent / "fixtures/parser_v3/team8-reference.xlsm"
    parsed = parse_workbook(path.read_bytes(), path.name)
    result = {item["tag"]: item for item in match_report(parsed)["results"]}
    assert len(result) == 7
    assert result["P-001"]["status"] == "no_match"
    assert result["R-001"]["status"] == "review"
    assert [c["name"] for c in result["S-001"]["candidates"]] == [
        "Thickeners and clarifiers"
    ]
    assert all(
        result[tag]["status"] == "match" for tag in ("T-001", "B-001", "T-002", "T-003")
    )


def test_both_garrett_files_and_index_bases_are_retained_separately():
    data = catalog()
    assert len(data["sources"]) == 2
    assert len({source["sha256"] for source in data["sources"]}) == 2
    bases = {source["id"]: source["index_basis"] for source in data["sources"]}
    assert {basis["value"] for basis in bases.values()} == {320}
    assert {basis["pdf_page"] for basis in bases.values()} == {5, 25}
    for item in data["equipment"]:
        assert len(item["source_refs"]) == 2
        refs = {ref["source_id"]: ref for ref in item["source_refs"]}
        assert (
            refs["garrett-1989-full-text"]["pdf_page"]
            - refs["garrett-1989-appendix-1"]["pdf_page"]
            == 261
        )
        assert len({ref["printed_page"] for ref in refs.values()}) == 1
    # Neither source has overwritten the independent costing engine's basis.
    from app.engine.costing import CostSettings

    assert CostSettings().cepci_base == 397
