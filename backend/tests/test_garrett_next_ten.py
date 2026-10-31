"""Source-transcription and arithmetic tests, not industrial calibration."""

import unittest
from dataclasses import replace
from math import inf, nan

from backend.equipment_costing.indexes.garrett import (
    classifiers,
    column_packing,
    columns,
    compressors_high_capacity_pressure,
    compressors_medium_low_pressure,
    conveyors,
    coolers_quenchers,
    cooling_towers,
    crystallizers,
    dryers,
)
from backend.equipment_costing.models import ReferenceCost


def reference(name, variant, unit, **changes):
    data = {
        "equipment": name,
        "variant": variant,
        "amount": 10000,
        "size": 100,
        "size_unit": unit,
        "currency": "USD",
        "cost_index": 320,
        "period": "early 1987",
        "source": "Synthetic test reference, not a graph-derived price",
        "valid_size_range": (50, 200),
        "same_configuration_confirmed": True,
    }
    data.update(changes)
    return ReferenceCost(**data)


CASES = [
    (classifiers, "classifiers", "rake", "source_ton_per_h", 1.32, 267),
    (
        compressors_medium_low_pressure,
        "compressors_medium_low_pressure",
        "straight_lobe",
        "scf_per_min",
        0.51,
        271,
    ),
    (
        compressors_high_capacity_pressure,
        "compressors_high_capacity_pressure",
        "centrifugal",
        "hp",
        0.80,
        272,
    ),
    (conveyors, "conveyors", "screw", "ft_length", 0.78, 273),
    (cooling_towers, "cooling_towers", "standard", "1000_gpm", 0.79, 275),
    (
        crystallizers,
        "crystallizers",
        "cooling_evaporative",
        "source_ton_per_h",
        0.68,
        276,
    ),
    (dryers, "dryers", "rotary", "ft2_peripheral_area", 0.45, 277),
]


class GarrettNextTenTests(unittest.TestCase):
    def test_reference_methods_and_both_boundary_directions(self):
        for module, name, variant, unit, n, page in CASES:
            ref = reference(name, variant, unit)
            for target, anchor in [(100, None), (400, 200), (25, 50)]:
                with self.subTest(name=name, target=target):
                    result = module.estimate_cost(target, ref)
                    self.assertAlmostEqual(result.amount, 10000 * (target / 100) ** n)
                    self.assertEqual(result.extrapolated, anchor is not None)
                    self.assertEqual(result.anchor_size, anchor)
                    if anchor:
                        self.assertAlmostEqual(
                            result.anchor_cost, 10000 * (anchor / 100) ** n
                        )
                    self.assertEqual(
                        (result.printed_page, result.pdf_page), (page, page - 250)
                    )
                    self.assertEqual(
                        (result.currency, result.cost_index, result.period),
                        ("USD", 320, "early 1987"),
                    )
                    self.assertIs(result.reference, ref)

    def test_columns_use_weight_and_printed_range(self):
        ref = reference(
            "columns",
            "weight_basis",
            "lb_column_weight",
            size=200000,
            valid_size_range=(10000, 2000000),
        )
        for target, anchor in [(50000, 100000), (2000000, 1000000)]:
            result = columns.estimate_cost(target, ref)
            self.assertTrue(result.extrapolated)
            self.assertEqual(result.anchor_size, anchor)
            self.assertAlmostEqual(result.amount, 10000 * (target / 200000) ** 0.78)
        with self.assertRaises(ValueError):
            columns.estimate_cost(200000, replace(ref, size=50000))
        with self.assertRaises(ValueError):
            columns.estimate_cost(200000, replace(ref, size_unit="ft_diameter"))

    def test_packing_is_scoped_unit_price_and_negative_exponent(self):
        ref = reference(
            "column_packing",
            "raschig_rings_porcelain",
            "in_nominal_packing_size",
            size=1,
            amount=10,
            valid_size_range=(0.5, 2),
            cost_scope="packing_unit_price_per_ft3",
        )
        result = column_packing.estimate_cost(4, ref)
        self.assertAlmostEqual(result.amount, 5)
        self.assertEqual(result.anchor_size, 2)
        self.assertEqual(result.exponent, -0.5)
        self.assertTrue(result.extrapolated)
        self.assertEqual(result.cost_scope, "packing_unit_price_per_ft3")
        self.assertEqual((result.printed_page, result.pdf_page), (270, 20))
        lower = column_packing.estimate_cost(0.25, ref)
        self.assertAlmostEqual(lower.amount, 20)
        self.assertEqual(lower.anchor_size, 0.5)
        with self.assertRaises(ValueError):
            column_packing.estimate_cost(
                1, replace(ref, cost_scope="purchased_equipment")
            )

    def test_source_variant_exponents(self):
        expected = [
            (classifiers, "spiral", 1.32),
            (column_packing, "berl_saddles_porcelain", -1.16),
            (column_packing, "pall_rings_stainless", -0.64),
            (column_packing, "pall_rings_polypropylene", -0.95),
            (column_packing, "interlox_saddles_porcelain", -0.4),
            (column_packing, "interlox_saddles_polypropylene", -0.95),
            (compressors_medium_low_pressure, "sliding_vane", 0.79),
            (compressors_medium_low_pressure, "helical_screw", 0.87),
            (compressors_medium_low_pressure, "reciprocating_air", 0.34),
            (compressors_high_capacity_pressure, "reciprocating", 0.8),
            (conveyors, "belt", 0.76),
            (conveyors, "bucket_elevator", 0.5),
            (conveyors, "roll", 0.5),
            (conveyors, "pneumatic", 0.37),
            (conveyors, "vibrating", 1),
            (crystallizers, "growth", 0.63),
            (crystallizers, "forced_circulation", 0.63),
            (crystallizers, "dtb", 0.63),
            (crystallizers, "vapor_recompression", 0.75),
            (dryers, "fluid_bed", 0.48),
            (dryers, "spray", 0.29),
        ]
        for module, variant, exponent in expected:
            name = module.__name__.split(".")[-1]
            unit = module.VARIANTS[variant][1]
            packing = name == "column_packing"
            ref = reference(
                name,
                variant,
                unit,
                amount=10 if packing else 10000,
                size=1 if packing else 100,
                valid_size_range=(0.5, 2) if packing else (50, 200),
                cost_scope="packing_unit_price_per_ft3"
                if packing
                else "purchased_equipment",
            )
            result = module.estimate_cost(ref.size * 2, ref)
            self.assertEqual(result.exponent, exponent)
            self.assertAlmostEqual(result.amount, ref.amount * 2**exponent)

    def test_cooler_and_quencher_explicit_equations(self):
        for variant, expected in [("spray_chamber", 100800), ("quencher", 45700)]:
            result = coolers_quenchers.estimate_cost(
                100, variant=variant, valid_flow_range=(10, 100)
            )
            self.assertEqual(result.amount, expected)
            self.assertFalse(result.extrapolated)
            self.assertEqual(result.size_unit, "1000_cfm_inlet")
            self.assertEqual((result.cost_index, result.period), (320, "early 1987"))
            self.assertEqual((result.printed_page, result.pdf_page), (274, 24))

    def test_direct_equation_extrapolates_from_top_and_bottom(self):
        upper = coolers_quenchers.estimate_cost(
            200, variant="quencher", valid_flow_range=(10, 100)
        )
        self.assertEqual(
            (upper.anchor_size, upper.anchor_cost, upper.amount), (100, 45700, 91400)
        )
        self.assertNotEqual(upper.amount, 335 * 200 + 12200)
        lower = coolers_quenchers.estimate_cost(
            5, variant="quencher", valid_flow_range=(10, 100)
        )
        self.assertEqual(
            (lower.anchor_size, lower.anchor_cost, lower.amount), (10, 15550, 7775)
        )
        self.assertTrue(upper.extrapolated and lower.extrapolated)
        override = coolers_quenchers.estimate_cost(
            200,
            variant="quencher",
            valid_flow_range=(10, 100),
            extrapolation_exponent=0.6,
        )
        self.assertAlmostEqual(override.amount, 45700 * 2**0.6)
        self.assertIn("assumption", override.exponent_basis)

    def test_dryer_volume_is_not_graph_axis_coordinate(self):
        ref = reference(
            "dryers", "spray", "ft3_volume", size=1000, valid_size_range=(500, 2000)
        )
        result = dryers.estimate_cost(2000, ref)
        self.assertAlmostEqual(result.amount, 10000 * 2**0.29)
        self.assertEqual(result.size, 2000)
        with self.assertRaises(ValueError):
            dryers.estimate_cost(2000, replace(ref, size_unit="ft2_peripheral_area"))

    def test_unknown_variants_and_invalid_inputs_remain_blocked(self):
        for module, name, variant, unit, _, _ in CASES:
            ref = reference(name, variant, unit)
            with self.assertRaises(ValueError):
                module.estimate_cost(100, replace(ref, variant="unlisted"))
            with self.assertRaises(ValueError):
                module.estimate_cost(nan, ref)
        for variant in ["cascade_cooler", "dilution_air_port"]:
            with self.assertRaises(ValueError):
                coolers_quenchers.estimate_cost(
                    20, variant=variant, valid_flow_range=(10, 100)
                )
        for bounds in [(0, 100), (100, 10), (10, inf), (nan, 100)]:
            with self.assertRaises(ValueError):
                coolers_quenchers.estimate_cost(
                    20, variant="quencher", valid_flow_range=bounds
                )
        with self.assertRaises(ValueError):
            coolers_quenchers.estimate_cost(
                20,
                variant="quencher",
                valid_flow_range=(10, 100),
                extrapolation_exponent=0,
            )


if __name__ == "__main__":
    unittest.main()
