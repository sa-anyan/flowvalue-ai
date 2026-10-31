"""Offline CAPEX source transcription, independent arithmetic and scope gates."""

import unittest
from dataclasses import replace
from decimal import Decimal as D
from unittest.mock import patch

from backend.capex import (
    CapexInputs,
    EquipmentCost,
    Override,
    WorkingCapital,
    calculate_capex,
    get_factor_ranges,
    get_model,
    list_models,
)
from backend.capex.advisor import CapexProposal, FactorProposal, validate_proposal
from backend.capex.connectors import prepare_capex_inputs


def equipment(**changes):
    return replace(
        EquipmentCost(
            "E-1",
            1000000,
            "USD",
            "early 1987",
            "CEPCI",
            320,
            delivery_basis="delivered",
        ),
        **changes,
    )


def inputs(**changes):
    return replace(
        CapexInputs((equipment(),), "solids", factor_selection="minimum"), **changes
    )


class CapexTests(unittest.TestCase):
    def test_registry_default_and_unsupported_method(self):
        self.assertEqual(get_model().id, "garrett")
        self.assertEqual(
            {m["id"] for m in list_models()},
            {"garrett", "nottingham", "nottingham_lang"},
        )
        self.assertEqual(sum(m["default"] for m in list_models()), 1)
        self.assertTrue(all(m["activation"] == "offline_only" for m in list_models()))
        with self.assertRaises(ValueError):
            get_model("turton_et_al")
        with self.assertRaises(ValueError):
            calculate_capex("unknown", inputs())

    def test_garrett_minimum_and_maximum_source_arithmetic(self):
        r = calculate_capex(inputs=inputs())
        self.assertEqual(r.direct_costs, D(1960000))
        self.assertEqual(r.indirect_costs, D(550000))
        self.assertEqual(r.plant_cost, D(2510000))
        self.assertEqual(r.working_capital, D(251000))
        self.assertEqual(r.startup_expenses, D(125500))
        self.assertEqual(r.total_capex, D(2886500))
        r = calculate_capex(
            inputs=inputs(
                factor_selection="maximum",
                offsite_scope_confirmation="Only external shared facilities, none in utilities/building/environmental scope",
            )
        )
        self.assertEqual(r.direct_costs, D(4800000))
        self.assertEqual(r.plant_cost, D(6800000))
        self.assertEqual(r.fixed_capital, D(8840000))
        self.assertEqual(r.working_capital, D(1360000))
        self.assertEqual(r.total_capex, D(10880000))

    def test_garrett_optional_subtotal_basis_is_not_purchase_basis(self):
        r = calculate_capex(inputs=inputs(indirect_basis="direct_costs"))
        self.assertEqual(r.direct_costs, D(1960000))
        self.assertEqual(r.indirect_costs, D(352800))
        self.assertEqual(r.plant_cost, D(2312800))
        fees = {line.id: line for line in r.lines}
        self.assertEqual(fees["construction_engineering"].base, "direct_costs")
        self.assertEqual(fees["construction_engineering"].base_amount, D(1960000))
        self.assertEqual(fees["contractor_fee"].amount, D(58800))
        r = calculate_capex(
            inputs=inputs(
                indirect_basis="direct_costs",
                factor_selection="maximum",
                offsite_scope_confirmation="separate scope",
            )
        )
        self.assertEqual(r.plant_cost, D(8160000))

    def test_garrett_installation_is_embedded_not_extra_63_percent(self):
        r = calculate_capex(inputs=inputs())
        line = next(l for l in r.lines if l.id == "equipment_installation")
        self.assertIsNone(line.amount)
        self.assertEqual(line.status, "embedded")
        self.assertEqual(r.direct_costs, D(1960000))
        bad = calculate_capex(
            inputs=inputs(selected_factors={"equipment_installation": ".63"})
        )
        self.assertIsNone(bad.total_capex)

    def test_garrett_all_categories_and_midpoints_are_explicit_assumptions(self):
        for category in ["solids", "mixed", "fluids"]:
            r = calculate_capex(
                inputs=inputs(
                    process_type=category,
                    factor_selection="midpoint",
                    offsite_scope_confirmation="nonoverlapping scope",
                )
            )
            self.assertIsNotNone(r.total_capex)
            self.assertTrue(any("midpoint" in s for s in r.assumptions))
        self.assertEqual(
            get_factor_ranges("garrett", "solids"),
            get_factor_ranges("garrett", "fluids"),
        )

    def test_selected_factors_and_out_of_range_overrides(self):
        selected = {
            f["id"]: f["minimum"]
            for f in get_factor_ranges("garrett", "solids")
            if f["additive"]
        }
        r = calculate_capex(
            inputs=inputs(factor_selection="selected", selected_factors=selected)
        )
        self.assertEqual(r.total_capex, D(2886500))
        bad = calculate_capex(inputs=inputs(selected_factors={"piping": ".99"}))
        self.assertIsNone(bad.total_capex)
        r = calculate_capex(
            inputs=inputs(
                overrides={
                    "piping": Override(
                        fraction=".99",
                        rationale="Quoted complex pipe scope",
                        source="User reviewed engineering scenario",
                    )
                }
            )
        )
        self.assertEqual(next(l.amount for l in r.lines if l.id == "piping"), D(990000))
        r = calculate_capex(
            inputs=inputs(
                overrides={
                    "piping": Override(
                        amount=123456,
                        rationale="Vendor estimate",
                        source="User supplied quote",
                    )
                }
            )
        )
        self.assertEqual(next(l.amount for l in r.lines if l.id == "piping"), D(123456))
        bad = calculate_capex(
            inputs=inputs(overrides={"piping": Override(amount=123456)})
        )
        self.assertIsNone(bad.total_capex)

    def test_unknown_and_conflicting_factors_not_silently_ignored(self):
        for kwargs in [
            {"selected_factors": {"bogus": ".2"}},
            {
                "selected_factors": {"piping": ".2"},
                "exclusions": {"piping": "existing"},
            },
            {
                "overrides": {"piping": Override(amount=5, rationale="test")},
                "selected_factors": {"piping": ".2"},
            },
        ]:
            self.assertIsNone(calculate_capex(inputs=inputs(**kwargs)).total_capex)

    def test_exclusions_with_reasons_and_offsite_scope(self):
        r = calculate_capex(
            inputs=inputs(
                exclusions={
                    "land": "Already owned",
                    "working_capital": "Separate financing scenario",
                }
            )
        )
        self.assertEqual(r.working_capital, 0)
        self.assertEqual(next(l.status for l in r.lines if l.id == "land"), "excluded")
        self.assertIsNone(
            calculate_capex(inputs=inputs(exclusions={"land": ""})).total_capex
        )
        bad = calculate_capex(
            inputs=inputs(selected_factors={"offsite_facilities": ".1"})
        )
        self.assertIsNone(bad.total_capex)
        self.assertTrue(any("Offsite allowance" in i for i in bad.issues))

    def test_garrett_working_capital_bases(self):
        plant = calculate_capex(
            inputs=inputs(
                working_capital=WorkingCapital(method="plant_fraction", fraction=".2")
            )
        )
        self.assertEqual(plant.working_capital, D(502000))
        annual = calculate_capex(
            inputs=inputs(
                working_capital=WorkingCapital(
                    method="annual_opex_fraction", fraction=".25", annual_opex=400000
                )
            )
        )
        self.assertEqual(annual.working_capital, D(100000))
        missing = calculate_capex(
            inputs=inputs(
                working_capital=WorkingCapital(
                    method="annual_opex_fraction", fraction=".25"
                )
            )
        )
        self.assertIsNone(missing.total_capex)
        absolute = calculate_capex(
            inputs=inputs(
                working_capital=WorkingCapital(
                    method="absolute",
                    amount=12345,
                    rationale="Itemized operating cash requirement",
                )
            )
        )
        self.assertEqual(absolute.working_capital, D(12345))

    def test_nottingham_profiles_reproduce_published_rounded_table(self):
        expected = {
            "solids": ("2640000", "3870000", "680000", "4550000"),
            "mixed": ("2930000", "4130000", "740000", "4870000"),
            "fluids": ("3460000", "4830000", "860000", "5690000"),
        }
        for category, values in expected.items():
            r = calculate_capex("nottingham", inputs(process_type=category))
            self.assertEqual(
                (r.direct_costs, r.fixed_capital, r.working_capital, r.total_capex),
                tuple(map(D, values)),
            )
            self.assertFalse(r.issues)
            installation = next(l for l in r.lines if l.id == "equipment_installation")
            self.assertEqual(installation.base, "purchased_equipment")
            self.assertGreater(installation.amount, 0)

    def test_nottingham_relationship_formulas_preserve_different_bases(self):
        r = calculate_capex("nottingham", inputs(factor_basis_mode="relationships"))
        self.assertEqual(r.plant_cost, D(3864000))
        fees = {l.id: l for l in r.lines}
        self.assertEqual(fees["contractor_fee"].base, "direct_and_indirect")
        self.assertEqual(fees["contractor_fee"].amount, D(168000))
        self.assertEqual(fees["contingency"].amount, D(336000))
        self.assertAlmostEqual(r.working_capital, D("681882.3529411764705882352941"))
        self.assertAlmostEqual(r.working_capital / r.total_capex, D(".15"))
        self.assertNotEqual(
            r.total_capex, calculate_capex("nottingham", inputs()).total_capex
        )

    def test_nottingham_months_of_opex_and_source_page(self):
        for months, expected in [(3, 100000), (6, 200000)]:
            r = calculate_capex(
                "nottingham",
                inputs(
                    working_capital=WorkingCapital(
                        method="months_opex", annual_opex=400000, months=months
                    )
                ),
            )
            self.assertEqual(r.working_capital, D(expected))
            self.assertEqual(
                next(
                    l.source.printed_page for l in r.lines if l.id == "working_capital"
                ),
                12,
            )
        self.assertIsNone(
            calculate_capex(
                "nottingham",
                inputs(
                    working_capital=WorkingCapital(
                        method="months_opex", annual_opex=400000, months=1
                    )
                ),
            ).total_capex
        )

    def test_lang_is_alternative_not_added_to_factorial(self):
        for category, factor in [
            ("solids", "3.1"),
            ("mixed", "3.6"),
            ("fluids", "4.7"),
            ("bioprocessing", "7.8"),
            ("water_treatment", "3.5"),
        ]:
            r = calculate_capex(
                "nottingham_lang",
                inputs(
                    process_type=category,
                    working_capital=WorkingCapital(
                        excluded=True, rationale="Compare fixed capital only"
                    ),
                ),
            )
            self.assertEqual(r.fixed_capital, D(1000000) * D(factor))
            self.assertEqual(r.total_capex, r.fixed_capital)
            self.assertEqual(r.indirect_costs, 0)
            self.assertEqual(sum(l.id == "lang_factor" for l in r.lines), 1)
            self.assertFalse(any(l.id == "piping" for l in r.lines))
        self.assertIsNone(
            calculate_capex(
                "nottingham_lang", inputs(selected_factors={"piping": ".2"})
            ).total_capex
        )

    def test_installed_module_delivery_and_mixed_basis_guards(self):
        for scope in ["installed_equipment", "module_estimate", "unit_price_per_ft"]:
            r = calculate_capex(inputs=inputs(equipment=(equipment(cost_scope=scope),)))
            self.assertIsNone(r.total_capex)
        self.assertIsNone(
            calculate_capex(
                "nottingham", inputs(equipment=(equipment(delivery_basis="ex_works"),))
            ).total_capex
        )
        for second in [
            equipment(tag="E-2", currency="GBP"),
            equipment(tag="E-2", period="2026"),
            equipment(tag="E-2", index_series="other"),
            equipment(tag="E-2", index_value=640),
        ]:
            self.assertIsNone(
                calculate_capex(
                    inputs=inputs(equipment=(equipment(), second))
                ).total_capex
            )

    def test_overlap_and_duplicate_equipment(self):
        overlap = equipment(included_categories=("piping",))
        self.assertIsNone(
            calculate_capex(inputs=inputs(equipment=(overlap,))).total_capex
        )
        r = calculate_capex(
            inputs=inputs(
                equipment=(overlap,),
                exclusions={"piping": "Already itemized in supplied price"},
            )
        )
        self.assertIsNotNone(r.total_capex)
        self.assertIsNone(
            calculate_capex(
                inputs=inputs(equipment=(equipment(), equipment(tag=" e-1 ")))
            ).total_capex
        )

    def test_missing_information_and_invalid_values(self):
        for change in [
            {"equipment": ()},
            {"process_type": None},
            {"process_type": "guess"},
            {"factor_selection": "unknown"},
            {"indirect_basis": "unknown"},
            {"factor_basis_mode": "guess"},
        ]:
            self.assertIsNone(calculate_capex(inputs=inputs(**change)).total_capex)
        self.assertIsNone(
            calculate_capex("nottingham", inputs(process_type=None)).total_capex
        )
        self.assertIsNone(
            calculate_capex(inputs=inputs(factor_selection="selected")).total_capex
        )
        for cost in [True, -1, float("nan"), float("inf")]:
            self.assertIsNone(
                calculate_capex(
                    inputs=inputs(equipment=(equipment(purchased_cost=cost),))
                ).total_capex
            )
        self.assertIsNone(
            calculate_capex(
                inputs=inputs(
                    working_capital=WorkingCapital(
                        method="total_investment_fraction", fraction=1, rationale="test"
                    )
                )
            ).total_capex
        )

    def test_switching_models_keeps_input_and_source_independent(self):
        original = inputs()
        g = calculate_capex("garrett", original)
        n = calculate_capex("nottingham", original)
        self.assertNotEqual(g.total_capex, n.total_capex)
        self.assertEqual(original.selected_factors, {})
        self.assertEqual(
            next(l.source.filename for l in g.lines if l.id == "piping"),
            "Chemical Engineering Economics for me.pdf",
        )
        self.assertEqual(
            next(l.source.filename for l in n.lines if l.id == "piping"),
            "CEEDG501 Cost Estimation Rev 3 (1).pdf",
        )
        rows = get_factor_ranges("garrett", "solids")
        rows[0]["formula"] = "tampered"
        self.assertNotEqual(
            get_factor_ranges("garrett", "solids")[0]["formula"], "tampered"
        )

    def test_connector_uses_quantity_extended_purchase_component_and_is_inactive(self):
        from backend.equipment_costing.total_cost import calculate_total_cost

        total = calculate_total_cost(
            [
                {
                    "equipment_tag": "HX-1",
                    "curve_id": "G287-092",
                    "size": 200,
                    "size_unit": "heat-transfer area, ft²",
                    "quantity": 2,
                    "costing_options": {
                        "allow_unverified": True,
                        "factors": ("287.material.316_stainless",),
                        "factor_basis_confirmation": "source basis",
                    },
                }
            ]
        )
        with patch(
            "backend.equipment_costing.registry.estimate_cost",
            side_effect=AssertionError("Must not recalculate equipment"),
        ):
            prepared = prepare_capex_inputs(
                total,
                process_type="solids",
                delivery_basis="delivered",
                factor_selection="minimum",
            )
        self.assertEqual(prepared.equipment[0].quantity, 1)
        self.assertEqual(
            prepared.equipment[0].purchased_cost, total.equipment_cost_total
        )
        self.assertNotEqual(
            prepared.equipment[0].purchased_cost,
            total.equipment_and_installation_cost_total,
        )
        self.assertTrue(prepared.equipment[0].provenance)
        self.assertIsNotNone(calculate_capex(inputs=prepared).total_capex)

    def test_connector_blocks_unresolved_purchase_split(self):
        from backend.equipment_costing.total_cost import calculate_total_cost

        total = calculate_total_cost(
            [
                {
                    "equipment_tag": "P-1",
                    "curve_id": "G294-117",
                    "size": 10,
                    "size_unit": "pipe diameter, in",
                    "quantity": 10,
                    "quantity_unit": "ft",
                    "costing_options": {"allow_unverified": True},
                }
            ]
        )
        with self.assertRaises(ValueError):
            prepare_capex_inputs(
                total, process_type="solids", delivery_basis="delivered"
            )

    def test_each_source_factor_range_and_nottingham_profile_entry(self):
        expected = {
            "piping": (".15", ".70"),
            "electrical": (".10", ".15"),
            "instrumentation_controls": (".10", ".35"),
            "utilities_services": (".30", ".75"),
            "foundations": (".07", ".12"),
            "insulation": (".02", ".08"),
            "painting_fire_safety": (".02", ".10"),
            "yard_improvements": (".05", ".15"),
            "environmental_controls": (".10", ".30"),
            "buildings": (".05", "1.00"),
            "land": ("0", ".10"),
        }
        ranges = {f["id"]: f for f in get_factor_ranges("garrett", "solids")}
        for name, (minimum, maximum) in expected.items():
            self.assertEqual(D(ranges[name]["minimum"]), D(minimum))
            self.assertEqual(D(ranges[name]["maximum"]), D(maximum))
            self.assertEqual(ranges[name]["base"], "purchased_equipment")
            self.assertEqual(ranges[name]["source"]["printed_page"], 29)
        expected_profiles = {
            "solids": [45, 9, 16, 10, 25, 13, 40, 6, 33, 39, 17, 34, 68],
            "mixed": [39, 13, 31, 10, 29, 10, 55, 6, 32, 34, 18, 36, 74],
            "fluids": [47, 18, 66, 11, 18, 10, 70, 6, 33, 41, 21, 42, 86],
        }
        for kind, percentages in expected_profiles.items():
            factors = [
                f for f in get_factor_ranges("nottingham", kind) if f["additive"]
            ]
            self.assertEqual(
                [D(f["minimum"]) * 100 for f in factors], list(map(D, percentages))
            )
            self.assertTrue(all(f["minimum"] == f["maximum"] for f in factors))

    def test_unpublished_nottingham_factors_remain_unavailable(self):
        rows = {f["id"]: f for f in get_factor_ranges("nottingham", "solids")}
        self.assertIsNone(rows["insulation"]["minimum"])
        self.assertFalse(rows["insulation"]["additive"])
        bad = calculate_capex(
            "nottingham", inputs(selected_factors={"insulation": ".05"})
        )
        self.assertIsNone(bad.total_capex)
        line = next(
            l
            for l in calculate_capex("nottingham", inputs()).lines
            if l.id == "insulation"
        )
        self.assertEqual(line.status, "not_separately_published")
        self.assertIsNone(line.amount)

    def test_conflicting_working_capital_inputs_and_month_defaults(self):
        bad = calculate_capex(
            inputs=inputs(
                selected_factors={"working_capital": ".1"},
                working_capital=WorkingCapital(fraction=".2"),
            )
        )
        self.assertIsNone(bad.total_capex)
        missing = calculate_capex("nottingham_lang", inputs())
        self.assertIsNone(missing.total_capex)
        self.assertTrue(any("months" in i for i in missing.issues))
        custom = calculate_capex(
            "nottingham_lang",
            inputs(
                working_capital=WorkingCapital(
                    method="months_opex",
                    annual_opex=120000,
                    months=9,
                    rationale="Long customer credit period, explicit scenario",
                )
            ),
        )
        self.assertEqual(custom.working_capital, D(90000))

    def test_quantity_multiplied_once_and_zero_override_is_preserved(self):
        r = calculate_capex(
            "nottingham",
            inputs(equipment=(equipment(purchased_cost=500000, quantity=2),)),
        )
        self.assertEqual(r.total_capex, D(4550000))
        r = calculate_capex(
            inputs=inputs(
                overrides={
                    "land": Override(amount=0, rationale="Owned site; documented zero")
                }
            )
        )
        land = next(l for l in r.lines if l.id == "land")
        self.assertEqual(land.amount, 0)
        self.assertEqual(land.status, "user_override")

    def test_garrett_installed_equipment_working_capital_alternative(self):
        r = calculate_capex(
            inputs=inputs(
                working_capital=WorkingCapital(
                    method="installed_equipment_fraction",
                    installed_equipment_cost=1600000,
                )
            )
        )
        self.assertEqual(r.working_capital, D(800000))
        self.assertEqual(
            next(l.source.printed_page for l in r.lines if l.id == "working_capital"),
            41,
        )
        missing = calculate_capex(
            inputs=inputs(
                working_capital=WorkingCapital(method="installed_equipment_fraction")
            )
        )
        self.assertIsNone(missing.total_capex)

    def test_future_advisor_draft_only_and_range_validation(self):
        source = get_model("garrett").source.reference
        proposal = CapexProposal(
            "garrett",
            "solids",
            "Substantial solids conveying",
            (
                FactorProposal(
                    "piping",
                    ".2",
                    "purchased_equipment",
                    "Limited fluid recycling",
                    (source,),
                ),
            ),
        )
        self.assertEqual(validate_proposal(proposal), ())
        bad = replace(
            proposal,
            factors=(
                FactorProposal("piping", "9", "purchased_equipment", "bad", (source,)),
            ),
        )
        self.assertTrue(validate_proposal(bad))
        bad = replace(
            proposal,
            factors=(FactorProposal("piping", ".2", "direct_costs", "bad", ()),),
        )
        self.assertTrue(validate_proposal(bad))
        self.assertEqual(inputs().selected_factors, {})


if __name__ == "__main__":
    unittest.main()
