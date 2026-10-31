"""Final appendix coverage, independent exponent expectations and scope guards."""

import importlib
import json
import unittest
from collections import Counter
from dataclasses import replace
from decimal import Decimal, localcontext
from math import inf, nan
from pathlib import Path

from backend.equipment_costing.models import ReferenceCost

CASES = [
    (
        "grinding_mills",
        292,
        "shredder",
        0.53,
        "source_ton_per_h",
        "purchased_equipment",
    ),
    (
        "grinding_mills",
        292,
        "mill_purchased",
        0.70,
        "source_ton_per_h",
        "purchased_equipment",
    ),
    (
        "grinding_mills",
        292,
        "mill_installed",
        0.62,
        "source_ton_per_h",
        "installed_equipment",
    ),
    ("motors_drives", 293, "small_electric_motor", 0.86, "hp", "purchased_equipment"),
    ("motors_drives", 293, "gas_turbine", 0.76, "hp", "purchased_equipment"),
    ("motors_drives", 293, "gas_engine", 0.76, "hp", "purchased_equipment"),
    ("motors_drives", 293, "steam_turbine", 0.41, "hp", "purchased_equipment"),
    (
        "pipe_pipelines",
        294,
        "pipeline",
        0.99,
        "in_pipe_size",
        "installed_pipeline_unit_price_per_ft",
    ),
    (
        "pumps_centrifugal",
        296,
        "axial_flow",
        0.79,
        "gpm_times_psi",
        "purchased_equipment",
    ),
    (
        "pumps_centrifugal",
        296,
        "mixed_flow",
        0.79,
        "gpm_times_psi",
        "purchased_equipment",
    ),
    *[
        ("pumps_miscellaneous", 297, v, n, u, "purchased_equipment")
        for v, n, u in [
            ("reciprocating", 0.59, "gpm_times_psi"),
            ("turbine", 0.47, "gpm_times_psi"),
            ("chemical_injection", 0.52, "source_flow_basis"),
            ("diaphragm", 0.43, "gpm_times_psi"),
            ("rotary", 0.52, "gpm_times_psi"),
            ("gear", 0.75, "source_gpm"),
            ("sump", 0.15, "gpm_times_psi"),
        ]
    ],
    (
        "pressure_vessels",
        298,
        "15_psi_volume",
        0.64,
        "source_gal",
        "purchased_equipment",
    ),
    ("refrigeration", 300, "40_F", 0.69, "refrigeration_ton", "purchased_equipment"),
    (
        "vibrating_screens",
        301,
        "single_deck",
        0.75,
        "ft2_screen_area",
        "purchased_equipment",
    ),
    *[
        ("size_enlargement", 302, v, n, "source_ton_per_h", "purchased_equipment")
        for v, n in [
            ("pug_mill", 0.15),
            ("pellet_mill", 0.12),
            ("pelletizing_rolls", 0.58),
        ]
    ],
    *[
        ("storage_tanks", 303, v, n, "source_gal", "purchased_equipment")
        for v, n in [
            ("small_cone_top", 0.51),
            ("large_cone_top", 0.51),
            ("horizontal_pressure", 0.72),
            ("sphere", 0.62),
            ("fiberglass", 0.71),
            ("small_storage", 0.71),
        ]
    ],
    *[
        ("small_stainless_tanks", 304, v, n, "source_gal", "purchased_equipment")
        for v, n in [
            ("dished_head_50_psi", 0.68),
            ("flanged_dished_head", 0.48),
            ("cone_top_bottom_legs", 0.57),
            ("flat_top_bottom", 0.93),
        ]
    ],
    (
        "thickeners_clarifiers",
        305,
        "rake_concrete_tank_drive",
        1.03,
        "ft_diameter",
        "purchased_equipment",
    ),
    (
        "vacuum_equipment",
        306,
        "vacuum_pump",
        0.75,
        "lb_per_h_air_per_mmHg_absolute",
        "purchased_equipment",
    ),
    (
        "vacuum_equipment",
        306,
        "steam_jet_ejector",
        0.42,
        "lb_per_h_air_per_mmHg_absolute",
        "purchased_equipment",
    ),
    (
        "vacuum_equipment",
        306,
        "barometric_condenser",
        0.67,
        "1000_source_gpm_water",
        "purchased_equipment",
    ),
]


def module(name):
    return importlib.import_module("backend.equipment_costing.indexes.garrett." + name)


def ref(name, variant, unit, scope):
    return ReferenceCost(
        equipment=name,
        variant=variant,
        amount=9753,
        size=100,
        size_unit=unit,
        cost_scope=scope,
        currency="EUR",
        cost_index=600,
        period="synthetic reference period",
        source="Synthetic arithmetic fixture, not a supplier price",
        valid_size_range=(50, 200),
        same_configuration_confirmed=True,
    )


class GarrettFinalEquipmentTests(unittest.TestCase):
    def test_all_final_variants_against_independent_decimal_scaling(self):
        with localcontext() as ctx:
            ctx.prec = 45
            for name, page, variant, n, unit, scope in CASES:
                reference = ref(name, variant, unit, scope)
                for target, anchor in [
                    (25, 50),
                    (50, None),
                    (150, None),
                    (200, None),
                    (400, 200),
                ]:
                    with self.subTest(name=name, variant=variant, target=target):
                        result = module(name).estimate_cost(target, reference)
                        expected = Decimal(9753) * (Decimal(target) / 100) ** Decimal(
                            str(n)
                        )
                        self.assertAlmostEqual(
                            result.amount / float(expected), 1, places=12
                        )
                        self.assertEqual(result.exponent, n)
                        self.assertEqual(result.extrapolated, anchor is not None)
                        self.assertEqual(result.anchor_size, anchor)
                        if anchor:
                            self.assertAlmostEqual(
                                result.anchor_cost, 9753 * (anchor / 100) ** n
                            )
                        self.assertEqual(
                            (result.printed_page, result.pdf_page), (page, page - 250)
                        )
                        self.assertEqual(
                            (result.currency, result.cost_index, result.period),
                            ("EUR", 600, "synthetic reference period"),
                        )
                        self.assertEqual(result.reference, reference)
                        self.assertEqual(result.cost_scope, scope)

    def test_invalid_sizes_scopes_units_and_variants_fail(self):
        for name, _, variant, _, unit, scope in CASES:
            reference = ref(name, variant, unit, scope)
            for target in [0, -1, nan, inf, True]:
                with self.assertRaises(ValueError):
                    module(name).estimate_cost(target, reference)
            for bad in [
                replace(reference, size_unit="wrong"),
                replace(reference, cost_scope="wrong"),
                replace(reference, variant="unknown"),
                replace(reference, equipment="other"),
            ]:
                with self.assertRaises(ValueError):
                    module(name).estimate_cost(100, bad)

    def test_graph_only_variants_are_not_silently_priced(self):
        for name, variant in [
            ("pumps_centrifugal", "conventional"),
            ("pumps_centrifugal", "inline"),
            ("pressure_vessels", "250_psi_volume"),
            ("pressure_vessels", "vertical_weight"),
            ("motors_drives", "large_electric_motor"),
            ("motors_drives", "variable_speed_drive"),
            ("pipe_pipelines", "bare_pipe"),
            ("pipe_pipelines", "submarine"),
            ("pumps_miscellaneous", "sliding_vane"),
            ("size_enlargement", "disk_granulator"),
        ]:
            with self.assertRaises(ValueError):
                module(name).estimate_cost(
                    100, ref(name, variant, "unknown", "purchased_equipment")
                )

    def test_installed_and_unit_price_references_cannot_be_treated_as_purchase_totals(
        self,
    ):
        for name, variant, unit, scope in [
            (
                "pipe_pipelines",
                "pipeline",
                "in_pipe_size",
                "installed_pipeline_unit_price_per_ft",
            ),
            (
                "grinding_mills",
                "mill_installed",
                "source_ton_per_h",
                "installed_equipment",
            ),
        ]:
            reference = ref(name, variant, unit, scope)
            with self.assertRaises(ValueError):
                module(name).estimate_cost(
                    100, replace(reference, cost_scope="purchased_equipment")
                )
            self.assertEqual(
                module(name).estimate_cost(100, reference).cost_scope, scope
            )

    def test_catalogue_covers_every_equipment_page_exactly_once(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "equipment_costing/indexes/garrett/catalogue.json"
        )
        data = json.loads(path.read_text())
        entries = data["entries"]
        self.assertEqual(len(entries), 51)
        self.assertEqual(
            sorted(e["printed_page"] for e in entries), list(range(256, 307))
        )
        self.assertEqual(
            Counter(e["category"] for e in entries),
            {"direct_price": 4, "reference_scaling": 39, "graph_only": 8},
        )
        self.assertEqual(
            {e["printed_page"] for e in entries if e["category"] == "graph_only"},
            {265, 269, 279, 281, 289, 291, 295, 299},
        )
        for entry in entries:
            self.assertEqual(entry["pdf_page"], entry["printed_page"] - 250)
            if entry["category"] == "graph_only":
                self.assertIsNone(entry["module"])
                self.assertTrue(entry["limitations"])
            else:
                implementation = module(entry["module"])
                self.assertTrue(callable(implementation.estimate_cost))
                self.assertTrue(entry["supported_variants"])
                if hasattr(implementation, "VARIANTS"):
                    self.assertEqual(
                        set(entry["supported_variants"]), set(implementation.VARIANTS)
                    )


if __name__ == "__main__":
    unittest.main()
