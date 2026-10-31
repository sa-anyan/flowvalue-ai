"""Independent arithmetic checks; not industrial calibration or source certification."""

import unittest
from dataclasses import replace
from math import inf, nan

from backend.equipment_costing.indexes.garrett import (
    activated_carbon_adsorbers,
    agitated_tanks,
    agitators,
    air_conditioning,
    blenders,
    blowers,
    boilers,
    buildings,
    chimneys_stacks,
    waste_heat_boilers,
)
from backend.equipment_costing.indexes.garrett.general import scale_cost
from backend.equipment_costing.models import ReferenceCost


def reference(equipment, variant, unit, **changes):
    data = {
        "equipment": equipment,
        "variant": variant,
        "amount": 10000,
        "size": 100,
        "size_unit": unit,
        "currency": "USD",
        "cost_index": 320,
        "period": "early 1987",
        "source": "Synthetic independent test reference, not a graph reading",
        "valid_size_range": (1, 10000),
        "same_configuration_confirmed": True,
    }
    data.update(changes)
    return ReferenceCost(**data)


class GarrettFirstTenTests(unittest.TestCase):
    def test_general_scaling_not_linear_or_inflation(self):
        self.assertAlmostEqual(scale_cost(100, 4, 9, 0.5), 150)
        self.assertEqual(scale_cost(125, 8, 8, 0.53), 125)
        self.assertAlmostEqual(scale_cost(100, 9, 4, 0.5), 100 / 1.5)

    def test_direct_adsorber_equations_independent_decimal_results(self):
        self.assertAlmostEqual(
            activated_carbon_adsorbers.estimate_cost(1000).amount,
            45706.521151170246,
            places=6,
        )
        self.assertAlmostEqual(
            activated_carbon_adsorbers.estimate_cost(20000).amount,
            137371.4036143975,
            places=6,
        )
        result = activated_carbon_adsorbers.estimate_cost(1000)
        self.assertEqual(
            (result.currency, result.cost_index, result.period, result.pdf_page),
            ("USD", 320, "early 1987", 6),
        )

    def test_strict_printed_adsorber_limits_and_gap(self):
        for weight in [0, 10000, -1, nan, inf, True]:
            with self.subTest(weight=weight), self.assertRaises(ValueError):
                activated_carbon_adsorbers.estimate_cost(weight)

    def test_each_scaling_module_uses_its_printed_exponent(self):
        cases = [
            (agitators, "agitators", "turbine", "hp", 100, 200, 0.68, 257),
            (
                agitated_tanks,
                "agitated_tanks",
                "standard",
                "US_gal",
                100,
                200,
                0.53,
                258,
            ),
            (
                air_conditioning,
                "air_conditioning",
                "standard",
                "refrigeration_ton",
                100,
                200,
                0.73,
                259,
            ),
            (blenders, "blenders", "ribbon", "ft3", 100, 200, 0.60, 260),
            (blowers, "blowers", "30_psi", "cfm", 100, 200, 0.52, 261),
            (boilers, "boilers", "package_hp", "boiler_hp", 100, 200, 0.65, 262),
            (
                waste_heat_boilers,
                "waste_heat_boilers",
                "standard",
                "1000_scfm",
                100,
                200,
                0.75,
                263,
            ),
            (buildings, "buildings", "office", "ft2", 100, 200, 0.8, 264),
            (chimneys_stacks, "chimneys_stacks", "tall", "ft", 300, 600, 1.63, 266),
        ]
        for module, name, variant, unit, s1, s2, n, page in cases:
            with self.subTest(name=name):
                scope = (
                    "building_cost" if name == "buildings" else "purchased_equipment"
                )
                ref = reference(name, variant, unit, size=s1, cost_scope=scope)
                result = module.estimate_cost(s2, ref)
                self.assertAlmostEqual(result.amount, 10000 * 2**n)
                self.assertEqual(result.exponent, n)
                self.assertEqual(
                    (result.printed_page, result.pdf_page), (page, page - 250)
                )
                self.assertIs(result.reference, ref)
                self.assertEqual(
                    (result.cost_index, result.period), (ref.cost_index, ref.period)
                )

    def test_alternate_variants_and_distinct_boiler_units(self):
        self.assertEqual(
            blenders.estimate_cost(
                100, reference("blenders", "double_cone", "ft3")
            ).exponent,
            0.42,
        )
        self.assertEqual(
            blowers.estimate_cost(100, reference("blowers", "10_psi", "cfm")).exponent,
            0.79,
        )
        self.assertEqual(
            boilers.estimate_cost(
                12000,
                reference(
                    "boilers",
                    "package_steam",
                    "lb_per_h_steam",
                    size=6000,
                    valid_size_range=(6000, 20000),
                ),
            ).exponent,
            0.77,
        )
        self.assertEqual(
            boilers.estimate_cost(
                12000,
                reference(
                    "boilers",
                    "field_erected",
                    "lb_per_h_steam",
                    size=6000,
                    valid_size_range=(6000, 20000),
                ),
            ).exponent,
            0.82,
        )
        self.assertTrue(
            boilers.estimate_cost(
                2000, reference("boilers", "package_hp", "boiler_hp")
            ).extrapolated
        )

    def test_agitator_bands_and_unsupported_variable_exponent(self):
        self.assertEqual(
            agitators.estimate_cost(
                2, reference("agitators", "turbine", "hp", size=1)
            ).exponent,
            0.23,
        )
        self.assertEqual(
            agitators.estimate_cost(
                20, reference("agitators", "turbine", "hp", size=10)
            ).exponent,
            0.56,
        )
        self.assertEqual(
            agitators.estimate_cost(
                2, reference("agitators", "propeller", "hp", size=1)
            ).exponent,
            0.42,
        )
        self.assertEqual(
            agitators.estimate_cost(
                10, reference("agitators", "propeller", "hp", size=5)
            ).exponent,
            0.51,
        )
        for ref, target in [
            (reference("agitators", "turbine", "hp", size=3), 10),
            (reference("agitators", "propeller", "hp", size=2), 10),
        ]:
            with self.assertRaises(ValueError):
                agitators.estimate_cost(target, ref)
        with self.assertRaises(ValueError):
            blowers.estimate_cost(200, reference("blowers", "under_3_psi", "cfm"))
        with self.assertRaises(ValueError):
            chimneys_stacks.estimate_cost(
                50, reference("chimneys_stacks", "short", "ft", size=20)
            )

    def test_metadata_units_and_extrapolation_guards(self):
        ref = reference(
            "agitated_tanks", "standard", "US_gal", valid_size_range=(50, 200)
        )
        before = ref.amount
        for changed in [
            replace(ref, size_unit="m3"),
            replace(ref, equipment="other"),
            replace(ref, cost_scope="installed"),
        ]:
            with self.assertRaises(ValueError):
                agitated_tanks.estimate_cost(150, changed)
        self.assertTrue(agitated_tanks.estimate_cost(201, ref).extrapolated)
        self.assertEqual(ref.amount, before)
        with self.assertRaises(ValueError):
            replace(ref, same_configuration_confirmed=False)
        with self.assertRaises(ValueError):
            replace(ref, source="")

    def test_reference_currency_and_index_not_implicitly_converted(self):
        ref = reference(
            "agitated_tanks",
            "standard",
            "US_gal",
            currency="GBP",
            cost_index=500,
            period="user reference period",
        )
        result = agitated_tanks.estimate_cost(200, ref)
        self.assertEqual(
            (result.currency, result.cost_index, result.period),
            ("GBP", 500, "user reference period"),
        )

    def test_adsorber_boundary_anchor_extrapolation(self):
        result = activated_carbon_adsorbers.estimate_cost(400000)
        anchor = 76200 + 0.422 * 200000**1.2
        self.assertTrue(result.extrapolated)
        self.assertEqual(result.anchor_size, 200000)
        self.assertAlmostEqual(result.anchor_cost, anchor)
        self.assertAlmostEqual(result.amount, anchor * 2**1.2)
        self.assertNotAlmostEqual(result.amount, 76200 + 0.422 * 400000**1.2)
        lower = activated_carbon_adsorbers.estimate_cost(125)
        self.assertEqual(lower.anchor_size, 250)
        self.assertAlmostEqual(lower.amount, lower.anchor_cost * 0.5**0.481)
        override = activated_carbon_adsorbers.estimate_cost(
            400000, extrapolation_exponent=0.6
        )
        self.assertAlmostEqual(override.amount, anchor * 2**0.6)
        for edge in (250, 200000):
            self.assertTrue(activated_carbon_adsorbers.estimate_cost(edge).extrapolated)

    def test_shared_boundary_scaling_preserves_reference_basis(self):
        ref = reference(
            "agitated_tanks", "standard", "US_gal", valid_size_range=(50, 200)
        )
        result = agitated_tanks.estimate_cost(400, ref)
        self.assertTrue(result.extrapolated)
        self.assertEqual(result.anchor_size, 200)
        self.assertAlmostEqual(result.anchor_cost, 10000 * 2**0.53)
        self.assertAlmostEqual(result.amount, result.anchor_cost * 2**0.53)
        self.assertEqual(
            (result.cost_index, result.period), (ref.cost_index, ref.period)
        )
        boiler = boilers.estimate_cost(
            2000, reference("boilers", "package_hp", "boiler_hp")
        )
        self.assertEqual(boiler.anchor_size, 1000)
        self.assertTrue(boiler.extrapolated)

    def test_invalid_general_inputs_fail_closed(self):
        for args in [
            (0, 1, 2, 0.5),
            (100, 0, 2, 0.5),
            (100, 1, nan, 0.5),
            (100, 1, 2, inf),
            (True, 1, 2, 0.5),
            (1, 1e-300, 1e300, 2),
        ]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                scale_cost(*args)


if __name__ == "__main__":
    unittest.main()
