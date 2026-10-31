"""Independent dimensional constants, context guards and costing reconciliation."""

import unittest
from dataclasses import asdict
from math import inf, nan

from backend.equipment_costing.registry import (
    estimate_cost,
    estimate_from_parsed_inputs,
    list_equipment_models,
    resolve_equipment_inputs,
)
from backend.equipment_costing.total_cost import calculate_total_cost
from backend.equipment_costing.unit_conversion import (
    ConversionContext,
    InputRequirement,
    Measurement,
    UnitResolutionError,
    convert,
    resolve_inputs,
)


class UnitConversionTests(unittest.TestCase):
    def test_mass_aliases_and_flow_time_bases(self):
        for unit in ["kg", "kilogram", "kilograms"]:
            self.assertAlmostEqual(convert(1, unit, "lb").value, 2.2046226218487757)
        self.assertAlmostEqual(convert(1, "tonnes/hour", "kg/s").value, 1000 / 3600)
        self.assertAlmostEqual(convert(1, "short ton", "kg").value, 907.18474)
        self.assertAlmostEqual(convert(1, "long ton", "kg").value, 1016.0469088)
        self.assertAlmostEqual(convert(1000, "grams", "kg").value, 1)
        self.assertAlmostEqual(convert(24, "kg/day", "kg/h").value, 1)
        self.assertAlmostEqual(convert(-1, "kg/h", "g/h").value, -1000)

    def test_ton_ambiguity_not_confused_with_refrigeration(self):
        self.assertEqual(convert(1, "ton", "kg").status, "unresolved")
        self.assertEqual(convert(1, "ton", "refrigeration_ton").status, "unresolved")
        ctx = ConversionContext(input_ton_basis="metric")
        self.assertEqual(convert(1, "ton", "kg", context=ctx).value, 1000)
        ctx = ConversionContext(target_ton_basis="short")
        self.assertAlmostEqual(
            convert(907.18474, "kg/h", "ton/h", context=ctx).value, 1
        )
        self.assertEqual(convert(1, "tonne", "refrigeration_ton").status, "unresolved")

    def test_volume_gallon_definitions_are_explicit(self):
        self.assertAlmostEqual(convert(1, "US gallon", "L").value, 3.785411784)
        self.assertAlmostEqual(convert(1, "imperial gallon", "L").value, 4.54609)
        self.assertEqual(convert(1, "gal", "L").status, "unresolved")
        self.assertEqual(convert(1, "gal", "gal").status, "unresolved")
        ctx = ConversionContext(input_gallon_basis="Imperial", target_gallon_basis="US")
        self.assertAlmostEqual(
            convert(1, "gal", "gal", context=ctx).value, 4.54609 / 3.785411784
        )
        self.assertAlmostEqual(convert(3.785411784, "L/min", "US_gpm").value, 1)

    def test_length_area_and_volume_dimensions(self):
        self.assertAlmostEqual(convert(25.4, "mm", "in").value, 1)
        self.assertAlmostEqual(convert(0.3048, "m", "ft").value, 1)
        self.assertAlmostEqual(convert(1, "m²", "ft2").value, 10.763910416709722)
        self.assertAlmostEqual(convert(1, "ft^3", "L").value, 28.316846592)
        self.assertEqual(convert(1, "ft2", "ft3").status, "unresolved")
        self.assertEqual(convert(100, "kg/h", "US_gal").status, "unresolved")

    def test_temperature_absolute_and_difference_separate(self):
        self.assertAlmostEqual(convert(0, "°C", "°F").value, 32)
        self.assertAlmostEqual(convert(100, "C", "K").value, 373.15)
        self.assertAlmostEqual(convert(32, "F", "C").value, 0)
        self.assertAlmostEqual(convert(10, "delta_C", "delta_F").value, 18)
        self.assertEqual(convert(10, "delta_C", "F").status, "unresolved")
        self.assertEqual(convert(-274, "degC", "K").status, "unresolved")
        self.assertAlmostEqual(convert(-459.67, "degF", "K").value, 0)

    def test_pressure_unit_scaling_preserves_basis(self):
        self.assertAlmostEqual(convert(1, "psi", "Pa").value, 6894.757293168361)
        self.assertEqual(convert(1, "bar", "kPa").value, 100)
        r = convert(1, "psig", "kPa")
        self.assertEqual(r.pressure_basis, "gauge")
        self.assertEqual(convert(1, "psig", "psia").status, "unresolved")
        ctx = ConversionContext(atmospheric_pressure_pa=101325)
        r = convert(0, "psig", "psia", context=ctx)
        self.assertAlmostEqual(r.value, 14.69594877551345)
        self.assertEqual(r.pressure_basis, "absolute")
        self.assertEqual(
            convert(1, "psig", "Pa", pressure_basis="absolute").status, "unresolved"
        )
        self.assertEqual(convert(-1, "psia", "Pa").status, "unresolved")
        self.assertEqual(convert(-20, "psig", "psia", context=ctx).status, "unresolved")

    def test_power_thermal_basis_and_symbol_case(self):
        self.assertAlmostEqual(
            convert(100, "refrigeration ton", "kW").value, 351.6852842066667
        )
        self.assertEqual(convert(1, "MW", "W").value, 1e6)
        self.assertEqual(convert(1, "mW", "W").value, 0.001)
        self.assertAlmostEqual(convert(1, "hp", "kW").value, 0.7456998715822702)
        self.assertEqual(convert(1, "boiler_hp", "kW").status, "unresolved")
        self.assertEqual(convert(1, "Btu/h", "W").status, "unresolved")
        self.assertAlmostEqual(
            convert(
                12000,
                "Btu/h",
                "refrigeration_ton",
                context=ConversionContext(btu_basis="IT"),
            ).value,
            1,
        )

    def test_gas_flows_do_not_assume_reference_states(self):
        self.assertEqual(convert(100, "scfm", "Nm3/h").status, "unresolved")
        self.assertEqual(convert(100, "m3/h", "scfm").status, "unresolved")
        ctx = ConversionContext(
            input_gas_reference="user stated 15 C, 101325 Pa",
            target_gas_reference="user stated 15 C, 101325 Pa",
        )
        self.assertAlmostEqual(
            convert(100, "scfm", "Sm3/h", context=ctx).value, 169.901079552
        )
        ctx = ConversionContext(input_gas_reference="0 C", target_gas_reference="15 C")
        self.assertEqual(
            convert(100, "scfm", "Sm3/h", context=ctx).status, "unresolved"
        )

    def test_density_molar_flow_and_compound_coordinate(self):
        self.assertEqual(convert(1, "g/cm3", "kg/m3").value, 1000)
        self.assertAlmostEqual(convert(1, "kmol/h", "mol/s").value, 1000 / 3600)
        self.assertEqual(convert(1, "kmol/h", "kg/h").status, "unresolved")
        self.assertEqual(convert(1, "US_gpm_psi", "1000 gpm_psi").status, "unresolved")
        ctx = ConversionContext(target_gallon_basis="US")
        self.assertAlmostEqual(
            convert(1000, "US_gpm_psi", "1000 gpm_psi", context=ctx).value, 1
        )

    def test_provenance_and_no_silent_number_parsing(self):
        source = {"sheet": "Streams", "cell": "B12"}
        r = convert(1, "kg", "lb", source=source)
        source["cell"] = "tampered"
        self.assertEqual(r.original.source["cell"], "B12")
        self.assertIn("original", asdict(r))
        for value in [True, nan, inf, "1,000"]:
            self.assertEqual(convert(value, "kg", "lb").status, "unresolved")
        self.assertEqual(convert(1, '__import__("os")', "kg").status, "unresolved")
        self.assertEqual(convert(1, "unknown", "kg").status, "unresolved")

    def test_resolver_never_uses_operating_pressure_for_design(self):
        required = [InputRequirement("design_pressure", "pressure", "psig")]
        r = resolve_inputs(required, {"operating_pressure": Measurement(10, "barg")})
        self.assertEqual(r.status, "needs_review")
        self.assertIn("Missing required input: design_pressure", r.issues)
        self.assertEqual(
            resolve_inputs(
                required, {"design_pressure": Measurement(10, "barg")}
            ).status,
            "resolved",
        )

    def test_registry_normalizes_size_and_preserves_all_three_prices(self):
        native = estimate_cost("G258-004", 100, size_unit="gal", allow_unverified=True)
        normalized = estimate_cost(
            "G258-004",
            0.3785411784,
            size_unit="m3",
            unit_context=ConversionContext(target_gallon_basis="US"),
            input_provenance={"sheet": "Units", "cell": "C2"},
            allow_unverified=True,
        )
        for attr in [
            "equipment_cost",
            "installation_cost",
            "equipment_and_installation_cost",
        ]:
            self.assertAlmostEqual(
                getattr(native, attr), getattr(normalized, attr), places=7
            )
        self.assertEqual(
            normalized.evidence["unit_conversion"]["size"]["original"]["source"][
                "cell"
            ],
            "C2",
        )
        with self.assertRaises(UnitResolutionError):
            estimate_cost("G258-004", 100, size_unit="L", allow_unverified=True)

    def test_refrigeration_and_area_chart_scaling(self):
        a = estimate_cost(
            "G259-009", 100, size_unit="refrigeration ton", allow_unverified=True
        )
        b = estimate_cost(
            "G259-009", 351.6852842066667, size_unit="kW", allow_unverified=True
        )
        self.assertAlmostEqual(a.amount, b.amount)
        r = estimate_cost("G286-091", 92.90304, size_unit="m2", allow_unverified=True)
        self.assertAlmostEqual(r.evidence["size_input"], 1)
        r = estimate_cost("G286-090", 0.9290304, size_unit="m2", allow_unverified=True)
        self.assertAlmostEqual(r.evidence["size_input"], 1)

    def test_parsed_adapter_optional_pressure_and_ambiguity(self):
        inputs = {
            "size": Measurement(200, "ft2", {"cell": "D5"}),
            "design_pressure": Measurement(10, "barg"),
            "temperature": Measurement(25, "degC"),
        }
        r = estimate_from_parsed_inputs("G287-092", inputs)
        self.assertAlmostEqual(r.evidence["normalized_context"]["temperature"], 77)
        self.assertIn("do not select curves", r.evidence["context_usage"])
        with self.assertRaises(UnitResolutionError):
            estimate_from_parsed_inputs(
                "G297-125",
                {"size": Measurement(1, "US_gpm_psi")},
                allow_unverified=True,
            )
        missing = resolve_equipment_inputs("G287-092", {})
        self.assertEqual(missing.status, "needs_review")

    def test_total_cost_inherits_shared_conversion(self):
        r = calculate_total_cost(
            [
                {
                    "equipment_tag": "T-1",
                    "curve_id": "G258-004",
                    "size": 0.3785411784,
                    "size_unit": "m3",
                    "costing_options": {
                        "allow_unverified": True,
                        "unit_context": ConversionContext(target_gallon_basis="US"),
                    },
                }
            ]
        )
        self.assertAlmostEqual(r.equipment_cost_total, 47070.10820099594)
        self.assertAlmostEqual(r.installation_cost_total, 28242.06492059757)
        self.assertAlmostEqual(
            r.equipment_and_installation_cost_total, 75312.17312159351
        )
        bad = calculate_total_cost(
            [
                {
                    "equipment_tag": "T-1",
                    "curve_id": "G258-004",
                    "size": 100,
                    "size_unit": "L",
                }
            ]
        )
        self.assertIsNone(bad.equipment_cost_total)

    def test_physical_quantities_are_converted_before_all_cost_components(self):
        r = calculate_total_cost(
            [
                {
                    "equipment_tag": "D-1",
                    "curve_id": "G278-063",
                    "size": 40,
                    "size_unit": "duct diameter, in",
                    "quantity": 100,
                    "quantity_unit": "m",
                }
            ]
        )
        self.assertAlmostEqual(r.equipment_cost_total, 64.18 * 100 / 0.3048)
        self.assertAlmostEqual(r.installation_cost_total, 64.18 * 100 / 0.3048 * 0.45)
        self.assertAlmostEqual(
            r.equipment_and_installation_cost_total, 64.18 * 100 / 0.3048 * 1.45
        )
        self.assertEqual(r.equipment[0].quantity_conversion.original.unit, "m")

    def test_round_trips_and_native_source_compatibility(self):
        for unit, target, value in [
            ("kg", "lb", 123.4),
            ("US_gal", "m3", 100),
            ("bar", "psi", 123),
            ("degC", "degF", -20),
            ("kW", "refrigeration_ton", 100),
            ("kg/h", "lb/h", 500),
        ]:
            first = convert(value, unit, target)
            second = convert(first.value, target, unit)
            self.assertAlmostEqual(second.value, value)
        r = estimate_cost(
            "G258-004",
            100,
            size_unit="gal",
            allow_unverified=True,
            input_provenance={"cell": "B2"},
        )
        self.assertEqual(r.evidence["native_input"]["source"]["cell"], "B2")
        self.assertNotIn("unit_conversion", r.evidence)

    def test_all_models_declare_requirements_and_do_not_expose_cache(self):
        models = list_equipment_models()
        self.assertEqual(len(models), 154)
        for m in models:
            self.assertEqual(m["input_requirements"][0]["name"], "size")
            self.assertTrue(
                m["input_requirements"][0]["target_unit"]
                or m["input_requirements"][0]["issue"]
            )
        models[0]["input_requirements"][0]["name"] = "tampered"
        self.assertEqual(
            list_equipment_models()[0]["input_requirements"][0]["name"], "size"
        )


if __name__ == "__main__":
    unittest.main()
