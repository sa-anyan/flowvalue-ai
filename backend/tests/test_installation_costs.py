"""PDF factors, component reconciliation, quantities, escalation and missing basis."""

import unittest
from dataclasses import asdict

from backend.equipment_costing.indexes.garrett.installation import installation_policy
from backend.equipment_costing.registry import estimate_cost, list_equipment_models
from backend.equipment_costing.total_cost import calculate_total_cost


class InstallationCostTests(unittest.TestCase):
    def setUp(self):
        self.models = {c["id"]: c for c in list_equipment_models()}

    def cost(self, cid, size, **options):
        return estimate_cost(
            cid,
            size,
            size_unit=self.models[cid]["size_unit"],
            allow_unverified=True,
            **options,
        )

    def item(self, tag, cid, size, **extra):
        return dict(
            equipment_tag=tag,
            curve_id=cid,
            size=size,
            size_unit=self.models[cid]["size_unit"],
            costing_options={"allow_unverified": True},
            **extra,
        )

    def test_autoclave_100_gallons_1500_psi_independent_source_factor(self):
        r = self.cost("G258-004", 100)
        self.assertAlmostEqual(r.equipment_cost, 47070.10820099594)
        self.assertAlmostEqual(r.installation_cost, 28242.064920597564)
        self.assertAlmostEqual(r.equipment_and_installation_cost, 75312.17312159351)
        self.assertEqual(r.installation.installation_factor, 1.6)
        self.assertEqual(r.installation.evidence["factor"]["range"], [1.5, 1.7])
        self.assertEqual(r.installation.evidence["factor"]["printed_page"], 258)
        self.assertEqual(r.estimate.cost_index, 320)

    def test_configuration_specific_tanks_and_agitators(self):
        for cid, size, factor in [
            ("G258-004", 100, 1.6),
            ("G258-005", 100, 1.6),
            ("G258-006", 100, 1.44),
            ("G258-007", 100, 1.44),
            ("G258-008", 100, 1.58),
            ("G257-002", 10, 1.32),
            ("G257-003", 10, 1.22),
        ]:
            r = self.cost(cid, size)
            self.assertEqual(r.installation.installation_factor, factor)
            self.assertAlmostEqual(r.installation_cost, r.equipment_cost * (factor - 1))
            self.assertAlmostEqual(
                r.equipment_and_installation_cost,
                r.equipment_cost + r.installation_cost,
            )

    def test_plate_frame_material_specific_factor_not_borrowed_for_spiral(self):
        ss = self.cost("G287-092", 200)
        self.assertEqual(ss.installation.installation_factor, 1.53)
        ms = self.cost(
            "G287-092",
            200,
            factors=("287.material.mild_steel",),
            factor_basis_confirmation="304 baseline converted to mild steel source factor",
        )
        self.assertEqual(ms.installation.installation_factor, 1.70)
        self.assertAlmostEqual(ms.equipment_cost, 100 * 200**0.78 * 0.43)
        nickel = self.cost(
            "G287-092",
            200,
            factors=("287.material.nickel",),
            factor_basis_confirmation="nickel construction scenario",
        )
        self.assertIsNone(nickel.installation_cost)
        spiral = self.cost("G287-093", 100)
        self.assertGreater(spiral.equipment_cost, 0)
        self.assertIsNone(spiral.installation_cost)
        self.assertIsNone(spiral.equipment_and_installation_cost)

    def test_pump_subtypes_and_ambiguous_merged_curve(self):
        for cid, factor in [
            ("G296-122", 1.30),
            ("G296-123", 1.27),
            ("G297-127", 1.74),
            ("G297-128", 1.38),
        ]:
            r = self.cost(cid, 100)
            self.assertEqual(r.installation.installation_factor, factor)
        combined = self.cost("G296-124", 100)
        self.assertIsNone(combined.installation_cost)
        axial = self.cost("G296-124", 100, installation_variant="axial_flow")
        mixed = self.cost("G296-124", 100, installation_variant="mixed_flow")
        self.assertEqual(axial.installation.installation_factor, 1.58)
        self.assertEqual(mixed.installation.installation_factor, 1.32)
        invalid = self.cost("G296-124", 100, installation_variant="guessed")
        self.assertIsNone(invalid.amount)

    def test_explicit_installation_factor_not_applied_twice(self):
        r = self.cost(
            "G258-004",
            100,
            factors=("258.installation.autoclave",),
            factor_basis_confirmation="1500 psi autoclave source basis",
        )
        self.assertAlmostEqual(r.amount, 47070.10820099594 * 1.6)
        self.assertAlmostEqual(r.equipment_cost, 47070.10820099594)
        self.assertAlmostEqual(r.equipment_and_installation_cost, r.amount)
        module = self.cost(
            "G258-004",
            100,
            factors=("258.module.standard",),
            factor_basis_confirmation="source module scenario",
        )
        self.assertAlmostEqual(module.amount, module.equipment_cost * 2.5)
        self.assertAlmostEqual(
            module.equipment_and_installation_cost, module.equipment_cost * 1.6
        )

    def test_missing_source_factor_is_unknown_not_zero_or_module(self):
        for cid, size in [
            ("G256-001", 1),
            ("G264-022", 1000),
            ("G288-094", 10),
            ("G304-148", 10),
        ]:
            r = self.cost(cid, size)
            self.assertIsNone(r.installation_cost)
            self.assertIsNone(r.equipment_and_installation_cost)
            self.assertIsNone(r.installation.installation_factor)

    def test_already_installed_source_prices_not_double_counted_or_reverse_inferred(
        self,
    ):
        for cid, size in [("G289-098", 10), ("G294-117", 10)]:
            r = self.cost(cid, size)
            self.assertIsNone(r.equipment_cost)
            self.assertIsNone(r.installation_cost)
            self.assertAlmostEqual(r.equipment_and_installation_cost, r.amount)
            self.assertEqual(r.installation.status, "already_included_unsplit")

    def test_all_three_components_escalate_together(self):
        historical = self.cost("G258-004", 100)
        future = self.cost(
            "G258-004",
            100,
            target_index=640,
            target_period="test",
            target_index_source="synthetic scenario",
        )
        for key in [
            "equipment_cost",
            "installation_cost",
            "equipment_and_installation_cost",
        ]:
            self.assertAlmostEqual(getattr(future, key), getattr(historical, key) * 2)
        self.assertAlmostEqual(
            future.installation.evidence["historical_installation_cost"],
            historical.installation_cost,
        )

    def test_total_cost_shows_three_separate_reconciled_totals(self):
        r = calculate_total_cost(
            [
                self.item("T-1", "G258-004", 100, quantity=2),
                self.item("HX-1", "G287-092", 200),
            ]
        )
        equipment = 2 * 47070.10820099594 + 100 * 200**0.78
        installation = 2 * 47070.10820099594 * 0.60 + 100 * 200**0.78 * 0.53
        self.assertAlmostEqual(r.equipment_cost_total, equipment)
        self.assertAlmostEqual(r.installation_cost_total, installation)
        self.assertAlmostEqual(
            r.equipment_and_installation_cost_total, equipment + installation
        )
        self.assertEqual(r.cost_breakdown_status, "provisional")
        self.assertEqual(len(r.component_subtotals), 1)
        self.assertAlmostEqual(r.equipment[0].installation_cost, 2 * 28242.064920597564)
        payload = asdict(r)
        self.assertIn("installation_cost_total", payload)
        self.assertIn("installation_cost", payload["equipment"][0])

    def test_unit_quantities_extend_each_component(self):
        r = calculate_total_cost(
            [self.item("D-1", "G278-063", 40, quantity=100, quantity_unit="ft")]
        )
        self.assertAlmostEqual(r.equipment_cost_total, 64.18 * 100)
        self.assertAlmostEqual(r.installation_cost_total, 64.18 * 100 * 0.45)
        self.assertAlmostEqual(
            r.equipment_and_installation_cost_total, 64.18 * 100 * 1.45
        )

    def test_partial_missing_installation_does_not_hide_equipment_total(self):
        r = calculate_total_cost(
            [self.item("T-1", "G258-004", 100), self.item("A-1", "G256-001", 1)]
        )
        self.assertGreater(r.equipment_cost_total, 0)
        self.assertIsNone(r.installation_cost_total)
        self.assertIsNone(r.equipment_and_installation_cost_total)
        self.assertEqual(r.component_subtotals[0].missing_installation_tags, ("A-1",))
        self.assertTrue(r.installation_issues)

    def test_mixed_index_and_unresolved_items_suppress_complete_component_totals(self):
        a = self.item("T-1", "G258-004", 100)
        b = self.item("T-2", "G258-004", 100)
        b["costing_options"].update(
            target_index=640, target_period="test", target_index_source="synthetic"
        )
        r = calculate_total_cost([a, b])
        self.assertIsNone(r.equipment_cost_total)
        self.assertIsNone(r.installation_cost_total)
        self.assertIsNone(r.equipment_and_installation_cost_total)
        self.assertEqual(len(r.component_subtotals), 2)
        r = calculate_total_cost([a, {"equipment_tag": "missing"}])
        self.assertIsNone(r.equipment_and_installation_cost_total)

    def test_every_curve_has_explicit_installation_metadata(self):
        self.assertEqual(len(self.models), 154)
        for cid, model in self.models.items():
            policy = installation_policy(cid)
            self.assertEqual(policy, model["installation_policy"])
            self.assertEqual(policy["printed_page"], model["printed_page"])
            self.assertTrue(policy["reason"])
            for factor in [policy["default"], *policy["choices"].values()]:
                if factor:
                    self.assertGreaterEqual(factor["multiplier"], 1)
                    self.assertEqual(factor["printed_page"], model["printed_page"])


if __name__ == "__main__":
    unittest.main()
