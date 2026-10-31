"""Independent source-value checks; synthetic references are not market prices."""

import unittest
from dataclasses import replace
from decimal import Decimal, localcontext
from math import inf, nan

from backend.equipment_costing.indexes.garrett import (
    ducts,
    electric_generators,
    evaporators,
    filters,
    flares,
    furnaces,
    heat_exchangers_shell_tube,
    heat_exchangers_spiral_plate,
    incinerators,
    ion_exchange,
)
from backend.equipment_costing.models import ReferenceCost

# Expected exponents and units transcribed independently from the reviewed pages.
CASES = [
    (evaporators, 280, "forced_circulation", 0.7, "ft2_heat_transfer_area"),
    *[
        (evaporators, 280, v, 0.53, "ft2_heat_transfer_area")
        for v in ("falling_film", "long_tube", "short_tube")
    ],
    *[
        (filters, 282, v, 0.39, "ft2_filter_area")
        for v in ("rotary_vacuum_drum", "rotary_leaf")
    ],
    *[
        (filters, 282, v, 0.5, "ft2_filter_area")
        for v in ("vacuum_table", "tilting_pan", "belt")
    ],
    *[
        (filters, 282, v, 0.61, "ft2_filter_area")
        for v in ("pressure_leaf", "plate_and_frame")
    ],
    (flares, 283, "elevated", 0.59, "lb_per_h_waste_gas"),
    (flares, 283, "ground", 0.39, "lb_per_h_waste_gas"),
    (furnaces, 284, "hershoff", 0.48, "MMBtu_per_h_transferred"),
    (furnaces, 284, "box", 0.70, "MMBtu_per_h_transferred"),
    (furnaces, 284, "cylindrical", 0.78, "MMBtu_per_h_transferred"),
    (electric_generators, 285, "diesel_drive", 0.71, "kW_electric_capacity"),
    (electric_generators, 285, "turbine_drive", 0.76, "kW_electric_capacity"),
    *[
        (heat_exchangers_shell_tube, 286, v, 0.68, "ft2_outside_heat_transfer_area")
        for v in ("shell_and_tube", "double_pipe")
    ],
    (
        heat_exchangers_shell_tube,
        286,
        "air_cooled",
        0.39,
        "ft2_outside_heat_transfer_area",
    ),
    (incinerators, 288, "rotary_kiln", 0.48, "MMBtu_per_h_heat_input"),
    (incinerators, 288, "hearth", 0.64, "MMBtu_per_h_heat_input"),
    (incinerators, 288, "catalytic", 0.75, "MMBtu_per_h_heat_input"),
    (incinerators, 288, "direct_flame", 0.39, "MMBtu_per_h_heat_input"),
    (ion_exchange, 290, "standard", 0.97, "gpm_water_treated"),
]


def ref(module, variant, unit):
    return ReferenceCost(
        equipment=module.__name__.split(".")[-1],
        variant=variant,
        amount=12345,
        size=100,
        size_unit=unit,
        currency="GBP",
        cost_index=500,
        period="synthetic test period",
        source="Synthetic arithmetic fixture, not market data",
        valid_size_range=(50, 200),
        same_configuration_confirmed=True,
    )


class GarrettThirdTenTests(unittest.TestCase):
    def test_all_reference_variants_and_both_boundary_directions(self):
        with localcontext() as ctx:
            ctx.prec = 45
            for module, page, variant, n, unit in CASES:
                reference = ref(module, variant, unit)
                for target, anchor in [
                    (25, 50),
                    (50, None),
                    (150, None),
                    (200, None),
                    (400, 200),
                ]:
                    with self.subTest(
                        module=module.__name__, variant=variant, target=target
                    ):
                        result = module.estimate_cost(target, reference)
                        expected = Decimal(12345) * (Decimal(target) / 100) ** Decimal(
                            str(n)
                        )
                        self.assertAlmostEqual(
                            result.amount / float(expected), 1, places=12
                        )
                        self.assertEqual(result.exponent, n)
                        self.assertEqual(result.anchor_size, anchor)
                        self.assertEqual(result.extrapolated, anchor is not None)
                        if anchor:
                            self.assertAlmostEqual(
                                result.anchor_cost, 12345 * (anchor / 100) ** n
                            )
                        self.assertEqual(
                            (result.printed_page, result.pdf_page), (page, page - 250)
                        )
                        self.assertEqual(
                            (result.currency, result.cost_index, result.period),
                            ("GBP", 500, "synthetic test period"),
                        )
                        self.assertEqual(result.reference, reference)
                        self.assertEqual(len(result.source_sha256), 64)

    def test_duct_equations_are_per_foot_not_total_or_thousands(self):
        for variant, expected in [
            ("mild_steel", 14.38),
            ("stainless", 51.97),
            ("water_cooled", 146.8),
        ]:
            result = ducts.estimate_cost(
                10, variant=variant, valid_diameter_range=(2, 20)
            )
            self.assertAlmostEqual(result.amount, expected)
            self.assertEqual(result.cost_scope, "duct_unit_price_per_ft")
            self.assertEqual(result.size_unit, "in_duct_diameter")
            self.assertEqual(
                (result.currency, result.cost_index, result.period),
                ("USD", 320, "early 1987"),
            )
            self.assertEqual((result.printed_page, result.pdf_page), (278, 28))

    def test_duct_extrapolation_uses_boundary_not_affine_target(self):
        for target, anchor in [(1, 2), (40, 20)]:
            result = ducts.estimate_cost(
                target, variant="mild_steel", valid_diameter_range=(2, 20)
            )
            cost = -2.22 + 1.66 * anchor
            self.assertAlmostEqual(result.amount, cost * (target / anchor) ** 1.08)
            self.assertNotAlmostEqual(result.amount, -2.22 + 1.66 * target)
            self.assertEqual(result.anchor_size, anchor)
            self.assertAlmostEqual(result.anchor_cost, cost)
            self.assertTrue(result.extrapolated)

    def test_heat_exchanger_direct_equations_against_decimal(self):
        with localcontext() as ctx:
            ctx.prec = 45
            for variant, coefficient, exponent in [
                ("spiral_plate", 660, "0.59"),
                ("plate_and_frame", 100, "0.78"),
            ]:
                result = heat_exchangers_spiral_plate.estimate_cost(
                    100, variant=variant, valid_area_range=(20, 1000)
                )
                expected = Decimal(coefficient) * Decimal(100) ** Decimal(exponent)
                self.assertAlmostEqual(result.amount, float(expected), places=8)
                self.assertFalse(result.extrapolated)
                self.assertEqual(result.cost_scope, "purchased_equipment")
                self.assertEqual((result.printed_page, result.pdf_page), (287, 37))

    def test_heat_exchanger_boundary_anchors(self):
        for variant, k, n in [
            ("spiral_plate", 660, 0.59),
            ("plate_and_frame", 100, 0.78),
        ]:
            for target, anchor in [(10, 20), (2000, 1000)]:
                result = heat_exchangers_spiral_plate.estimate_cost(
                    target, variant=variant, valid_area_range=(20, 1000)
                )
                self.assertEqual(result.anchor_size, anchor)
                self.assertAlmostEqual(result.anchor_cost, k * anchor**n)
                self.assertAlmostEqual(
                    result.amount, k * anchor**n * (target / anchor) ** n
                )
                self.assertTrue(result.extrapolated)

    def test_reference_scope_unit_and_configuration_guards(self):
        for module, _, variant, _, unit in CASES:
            reference = ref(module, variant, unit)
            for bad in [
                replace(reference, size_unit="wrong"),
                replace(reference, cost_scope="installed"),
                replace(reference, variant="unknown"),
                replace(reference, equipment="other"),
            ]:
                with self.assertRaises(ValueError):
                    module.estimate_cost(100, bad)
            for size in [0, -1, nan, inf, True]:
                with self.assertRaises(ValueError):
                    module.estimate_cost(size, reference)

    def test_direct_methods_reject_invalid_inputs_and_nonpositive_anchor_prices(self):
        for variant in ["mild_steel", "stainless"]:
            with self.assertRaises(ValueError):
                ducts.estimate_cost(10, variant=variant, valid_diameter_range=(1, 20))
        for module, size_key, bounds_key, variant in [
            (ducts, "diameter_in", "valid_diameter_range", "mild_steel"),
            (
                heat_exchangers_spiral_plate,
                "area_ft2",
                "valid_area_range",
                "spiral_plate",
            ),
        ]:
            for size in [0, -1, nan, inf, True]:
                with self.assertRaises(ValueError):
                    module.estimate_cost(
                        **{size_key: size, bounds_key: (2, 20), "variant": variant}
                    )
            for bounds in [None, (20, 2), (0, 20), (2, inf), (nan, 20), [2, 20]]:
                with self.assertRaises(ValueError):
                    module.estimate_cost(
                        **{size_key: 10, bounds_key: bounds, "variant": variant}
                    )
            with self.assertRaises(ValueError):
                module.estimate_cost(
                    **{size_key: 10, bounds_key: (2, 20), "variant": "unknown"}
                )


if __name__ == "__main__":
    unittest.main()
