"""Registry, source lineage, provisional fitting, factors and index reconciliation."""

import json
import math
import unittest
from pathlib import Path

from backend.equipment_costing.cost_to_future.escalator import adjust_cost
from backend.equipment_costing.indexes.garrett.graph_models import fit_points
from backend.equipment_costing.registry import (
    estimate_cost,
    list_equipment_models,
    list_factors,
)


def point(x, y, row, purpose="Fit"):
    return {
        "size": x,
        "source_price": y,
        "row": row,
        "cell_range": f"H{row}:L{row}",
        "purpose": purpose,
    }


class GarrettIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.curves = {c["id"]: c for c in list_equipment_models()}

    def cost(self, identifier, size, **kwargs):
        return estimate_cost(
            identifier, size, size_unit=self.curves[identifier]["size_unit"], **kwargs
        )

    def test_registry_all_51_groups_154_configurations_with_cell_lineage(self):
        self.assertEqual(len(self.curves), 154)
        self.assertEqual(
            {c["printed_page"] for c in self.curves.values()}, set(range(256, 307))
        )
        for c in self.curves.values():
            self.assertTrue(c["register_cell_range"])
            self.assertTrue(c["configuration"])
            for p in c["points"]:
                self.assertTrue(p["cell_range"])
                self.assertEqual(p["size_unit"], c["size_unit"])
        a = list_equipment_models()
        a[0]["configuration"] = "tampered"
        self.assertNotEqual(list_equipment_models()[0]["configuration"], "tampered")

    def test_direct_equations_are_authoritative_despite_bad_graph_readings(self):
        for identifier, size, expected in [
            ("G256-001", 1, 45706.521151170244),
            ("G274-054", 100, 45700),
            ("G274-055", 50, 82900),
            ("G278-063", 40, 64.18),
            ("G278-064", 40, 227.17),
            ("G287-092", 200, 100 * 200**0.78),
            ("G287-093", 100, 660 * 100**0.59),
        ]:
            result = self.cost(identifier, size)
            self.assertAlmostEqual(result.amount, expected)
            self.assertEqual(result.status, "formula_estimate")
            self.assertEqual(result.estimate.cost_index, 320)
            self.assertTrue(result.evidence["workbook_sha256"])
        self.assertEqual(
            self.cost("G278-063", 40).estimate.cost_scope, "duct_unit_price_per_ft"
        )
        self.assertTrue(self.cost("G287-092", 200).fit_diagnostics)

    def test_graph_requires_provisional_opt_in(self):
        r = self.cost("G265-023", 20)
        self.assertIsNone(r.amount)
        self.assertEqual(r.status, "needs_review")
        r = self.cost("G265-023", 20, allow_unverified=True)
        self.assertGreater(r.amount, 0)
        self.assertEqual(r.status, "provisional")
        self.assertTrue(r.fit_diagnostics)

    def test_power_fit_independent_known_curve_and_holdout_exclusion(self):
        p = [point(1, 10, 2), point(4, 40, 3), point(2, 9999, 4, "Holdout")]
        fit = fit_points(p, multiplier=1)
        self.assertAlmostEqual(fit.exponent, 1)
        self.assertAlmostEqual(fit.evaluate(2), 20)
        self.assertEqual(fit.training_rows, (2, 3))
        self.assertEqual(len(fit.diagnostics), 3)
        fixed = fit_points([point(1, 10, 2), point(4, 80, 3)], multiplier=1, exponent=1)
        self.assertAlmostEqual(fixed.evaluate(1), math.sqrt(200))

    def test_invalid_duplicate_and_nonfinite_graph_data_rejected(self):
        for points in [
            [point(1, 10, 2)],
            [point(1, 10, 2), point(1, 20, 3)],
            [point(1, 10, 2), point(2, -1, 3)],
            [point(1, 10, 2), point(math.nan, 20, 3)],
        ]:
            with self.assertRaises(ValueError):
                fit_points(points, multiplier=1)
        fit = fit_points([point(1, 10, 2), point(4, 5, 3)], multiplier=1, exponent=-0.5)
        self.assertAlmostEqual(fit.evaluate(4), 5)

    def test_fitted_extrapolation_requires_justification(self):
        blocked = self.cost("G265-023", 1000, allow_unverified=True)
        self.assertIsNone(blocked.amount)
        approved = self.cost(
            "G265-023",
            1000,
            allow_unverified=True,
            extrapolation_exponent=0.7,
            extrapolation_justification="Synthetic scenario assumption, not source validated",
        )
        self.assertGreater(approved.amount, 0)
        self.assertTrue(approved.estimate.extrapolated)
        self.assertEqual(approved.estimate.anchor_size, 55)
        self.assertAlmostEqual(
            approved.amount, approved.estimate.anchor_cost * (1000 / 55) ** 0.7
        )

    def test_printed_exponent_boundary_and_lower_anchor(self):
        for size, bound in [(0.1, 1), (1000, 200)]:
            r = self.cost("G259-009", size, allow_unverified=True)
            self.assertTrue(r.estimate.extrapolated)
            self.assertEqual(r.estimate.anchor_size, bound)
            self.assertAlmostEqual(
                r.amount, r.estimate.anchor_cost * (size / bound) ** 0.73
            )

    def test_direct_affine_extrapolation_requires_caller_basis(self):
        self.assertIsNone(self.cost("G274-054", 200).amount)
        r = self.cost(
            "G274-054",
            200,
            extrapolation_exponent=0.8,
            extrapolation_justification="Reviewed scenario assumption",
        )
        self.assertAlmostEqual(r.amount, 45700 * 2**0.8)
        self.assertTrue(r.estimate.extrapolated)

    def test_conflicting_units_missing_points_and_branch_gap_are_explicit(self):
        for identifier, size in [
            ("G277-060", 100),
            ("G277-062", 100),
            ("G297-125", 10),
            ("G297-126", 10),
            ("G306-153", 1),
            ("G306-154", 1),
            ("G273-049", 100),
            ("G256-001", 10),
        ]:
            r = self.cost(identifier, size, allow_unverified=True)
            self.assertEqual(r.status, "needs_review")
            self.assertIsNone(r.amount)
            self.assertTrue(r.issues)

    def test_unit_and_source_validation(self):
        with self.assertRaises(ValueError):
            estimate_cost("G259-009", 100, size_unit="kg")
        with self.assertRaises(ValueError):
            estimate_cost("pump", 100, size_unit="kg")
        with self.assertRaises(ValueError):
            list_equipment_models("unknown")
        for size in [0, -1, True, math.nan, math.inf]:
            with self.assertRaises(ValueError):
                self.cost("G259-009", size)

    def test_factor_selection_confirmation_scopes_and_no_double_counting(self):
        kwargs = {
            "allow_unverified": True,
            "factor_basis_confirmation": "304 stainless no-insulation baseline; change to 316 stainless",
        }
        r = self.cost(
            "G287-092", 200, factors=("287.material.316_stainless",), **kwargs
        )
        self.assertAlmostEqual(r.amount, 100 * 200**0.78 * 1.1)
        self.assertEqual(len(r.applied_factors), 1)
        self.assertEqual(r.status, "provisional")
        missing = self.cost(
            "G287-092",
            200,
            allow_unverified=True,
            factors=("287.material.316_stainless",),
        )
        self.assertIsNone(missing.amount)
        for factors in [
            ("287.material.316_stainless", "287.material.316_stainless"),
            ("287.material.316_stainless", "287.material.titanium"),
            ("306.module.standard",),
        ]:
            self.assertIsNone(
                self.cost("G287-092", 200, factors=factors, **kwargs).amount
            )
        self.assertIsNone(
            self.cost(
                "G275-056",
                100,
                factors=("275.module.standard", "275.installation.source_average"),
                **kwargs,
            ).amount
        )
        self.assertIsNone(
            self.cost("G294-117", 10, factors=("294.module.unknown",), **kwargs).amount
        )

    def test_module_and_index_pipeline_reconciles(self):
        base = self.cost("G275-056", 100, allow_unverified=True)
        r = self.cost(
            "G275-056",
            100,
            allow_unverified=True,
            factors=("275.module.standard",),
            factor_basis_confirmation="Source thermal condition and baseline construction retained",
            target_index=640,
            target_period="synthetic future",
            target_index_source="Synthetic test index, not a published observation",
        )
        self.assertAlmostEqual(r.historical_amount, base.amount * 1.7)
        self.assertAlmostEqual(r.amount, base.amount * 1.7 * 2)
        self.assertEqual(r.estimate.cost_scope, "module_estimate")
        self.assertEqual(r.estimate.cost_index, 640)
        self.assertEqual(r.index_adjustment["base_index"], 320)
        self.assertEqual(r.estimate.currency, "USD")

    def test_index_series_and_missing_provenance_rejected(self):
        self.assertEqual(
            adjust_cost(
                100,
                base_index=320,
                target_index=800,
                base_series="CEPCI",
                target_series="CEPCI",
                target_period="test",
                target_source="test",
            ),
            250,
        )
        for params in [
            {
                "index_series": "other",
                "target_period": "test",
                "target_index_source": "test",
            },
            {"target_period": None, "target_index_source": "test"},
            {"target_period": "test", "target_index_source": None},
        ]:
            r = self.cost("G287-092", 200, target_index=800, **params)
            self.assertIsNone(r.amount)

    def test_all_groups_have_at_least_one_usable_configuration(self):
        supported = set()
        for c in self.curves.values():
            for p in c["points"]:
                if p["size"] is None:
                    continue
                r = self.cost(c["id"], p["size"], allow_unverified=True)
                if r.amount is not None:
                    supported.add(c["printed_page"])
                    break
        self.assertEqual(supported, set(range(256, 307)))

    def test_agitator_power_bands_never_mix_reference_points(self):
        small = self.cost("G257-002", 2, allow_unverified=True)
        self.assertAlmostEqual(small.amount, 6000 * 2**0.23)
        self.assertEqual(small.evidence["fit"]["training_rows"], (9,))
        middle = self.cost("G257-002", 10, allow_unverified=True)
        self.assertEqual(middle.estimate.exponent, 0.56)
        self.assertEqual(middle.evidence["fit"]["training_rows"], (10, 12))
        large = self.cost("G257-002", 60, allow_unverified=True)
        self.assertEqual(large.estimate.exponent, 0.68)
        self.assertNotIn(12, large.evidence["fit"]["training_rows"])

    def test_fit_diagnostics_cannot_mutate_cached_results(self):
        a = self.cost("G265-023", 20, allow_unverified=True)
        first = a.fit_diagnostics[0]["observed"]
        a.fit_diagnostics[0]["observed"] = -999
        b = self.cost("G265-023", 20, allow_unverified=True)
        self.assertEqual(b.fit_diagnostics[0]["observed"], first)

    def test_factor_catalogue_all_ids_unique_and_scoped(self):
        p = (
            Path(__file__).resolve().parents[1]
            / "equipment_costing/indexes/garrett/data/factors.json"
        )
        fs = json.loads(p.read_text())
        self.assertEqual(len(fs), len({f["id"] for f in fs}))
        for f in fs:
            self.assertGreater(f["multiplier"], 0)
            self.assertTrue(f["allowed_curve_ids"])
            for identifier in f["allowed_curve_ids"]:
                self.assertEqual(
                    self.curves[identifier]["printed_page"], f["printed_page"]
                )
        a = list_factors("G287-092")
        a[0]["multiplier"] = 99999
        self.assertNotEqual(list_factors("G287-092")[0]["multiplier"], 99999)


if __name__ == "__main__":
    unittest.main()
