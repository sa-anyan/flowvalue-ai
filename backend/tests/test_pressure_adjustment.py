"""Pressure basis, source/proxy selection and all-cost-component reconciliation."""

import unittest

from backend.equipment_costing.indexes.garrett.pressure_adjustment import (
    pressure_factor,
)
from backend.equipment_costing.registry import (
    PressureAdjustment,
    estimate_cost,
    estimate_from_parsed_inputs,
    list_equipment_models,
    list_pressure_methods,
)
from backend.equipment_costing.total_cost import calculate_total_cost
from backend.equipment_costing.unit_conversion import Measurement, UnitResolutionError


def request(method="garrett_power", value=105, unit="barg", **changes):
    args = {
        "method": method,
        "target_design_pressure": Measurement(
            value, unit, {"source": "synthetic design scenario"}
        ),
        "reference_pressure_basis": "gauge",
        "applicability_note": "Screening assumption: use vertical vessel pressure-factor ratio for same-size agitated autoclave; not mechanical design validation",
    }
    args.update(changes)
    return PressureAdjustment(**args)


class PressureAdjustmentTests(unittest.TestCase):
    def cost(self, req=None, **options):
        return estimate_cost(
            "G258-004",
            100,
            size_unit="gal",
            allow_unverified=True,
            pressure_adjustment=req,
            **options,
        )

    def test_105_bar_power_proxy_independent_ratio_and_components(self):
        base = self.cost()
        adjusted = self.cost(request())
        pressure_psi = 105 * 100000 / 6894.757293168361
        ratio = (pressure_psi / 1500) ** 0.44
        self.assertAlmostEqual(adjusted.equipment_cost, base.equipment_cost * ratio)
        self.assertAlmostEqual(
            adjusted.installation_cost, base.installation_cost * ratio
        )
        self.assertAlmostEqual(
            adjusted.equipment_and_installation_cost,
            base.equipment_and_installation_cost * ratio,
        )
        e = adjusted.evidence["pressure_adjustment"]
        self.assertEqual(e["applicability"], "provisional_agitated_vessel_proxy")
        self.assertEqual(e["source_printed_page"], 268)
        self.assertEqual(e["baseline_equipment_cost"], base.amount)
        self.assertEqual(adjusted.status, "provisional")
        self.assertEqual(adjusted.estimate.cost_index, 320)
        self.assertFalse(e["extrapolated"])

    def test_table_nodes_and_linear_interpolation(self):
        self.assertEqual(pressure_factor(1500, "garrett_table_linear"), 5.4)
        self.assertEqual(pressure_factor(2000, "garrett_table_linear"), 6.5)
        self.assertAlmostEqual(pressure_factor(1750, "garrett_table_linear"), 5.95)
        base = self.cost()
        r = self.cost(request("garrett_table_linear", 1750, "psig"))
        self.assertAlmostEqual(r.amount, base.amount * 5.95 / 5.4)
        self.assertIn(
            "implementation assumption",
            r.evidence["pressure_adjustment"]["interpolation_basis"],
        )

    def test_identity_and_return_to_original_do_not_change_baseline(self):
        base = self.cost()
        for method in ["garrett_power", "garrett_table_linear"]:
            same = self.cost(request(method, 1500, "psig"))
            self.assertAlmostEqual(same.amount, base.amount)
        self.cost(request())
        self.assertAlmostEqual(self.cost().amount, base.amount)
        self.assertNotIn("pressure_adjustment", self.cost().evidence)

    def test_pressure_basis_is_explicit_and_atmosphere_not_assumed(self):
        self.assertIsNone(self.cost(request(unit="bar")).amount)
        self.assertIsNone(self.cost(request(unit="bara")).amount)
        a = self.cost(request(unit="bara", atmospheric_pressure_pa=101325))
        self.assertIsNotNone(a.amount)
        self.assertAlmostEqual(
            a.evidence["pressure_adjustment"]["target_pressure_psi"],
            (10500000 - 101325) / 6894.757293168361,
        )
        self.assertIsNone(self.cost(request(reference_pressure_basis="unknown")).amount)

    def test_proxy_requires_approval_and_justification(self):
        r = estimate_cost(
            "G258-004", 100, size_unit="gal", pressure_adjustment=request()
        )
        self.assertIsNone(r.amount)
        self.assertIsNone(self.cost(request(applicability_note="")).amount)
        self.assertIsNone(self.cost(request(method="guess")).amount)

    def test_open_tank_and_other_equipment_do_not_accept_vessel_proxy(self):
        for cid, unit in [
            ("G258-008", "gal"),
            ("G259-009", "refrigeration ton"),
            ("G299-133", "reactor volume, 1,000 gal"),
        ]:
            r = estimate_cost(
                cid,
                100,
                size_unit=unit,
                allow_unverified=True,
                pressure_adjustment=request(),
            )
            self.assertIsNone(r.amount)

    def test_native_column_ratio_and_no_double_pressure_factor(self):
        base = estimate_cost(
            "G268-031", 5, size_unit="diameter, ft", allow_unverified=True
        )
        r = estimate_cost(
            "G268-031",
            5,
            size_unit="diameter, ft",
            allow_unverified=True,
            pressure_adjustment=request(
                value=100, unit="psig", method="garrett_table_linear"
            ),
        )
        self.assertAlmostEqual(r.amount, base.amount * 1.25)
        self.assertEqual(
            r.evidence["pressure_adjustment"]["applicability"], "source_vertical_column"
        )
        double = estimate_cost(
            "G268-031",
            5,
            size_unit="diameter, ft",
            allow_unverified=True,
            pressure_adjustment=request(),
            factors=("268.pressure.100_psi",),
            factor_basis_confirmation="test",
        )
        self.assertIsNone(double.amount)

    def test_vessel_reference_uses_factor_ratio_not_absolute_factor(self):
        base = estimate_cost(
            "G298-132",
            10,
            size_unit="vessel capacity, 1,000 gal",
            allow_unverified=True,
        )
        r = estimate_cost(
            "G298-132",
            10,
            size_unit="vessel capacity, 1,000 gal",
            allow_unverified=True,
            pressure_adjustment=request(
                value=500, unit="psig", method="garrett_table_linear"
            ),
        )
        self.assertAlmostEqual(r.amount, base.amount * 2.8 / 1.775)
        self.assertEqual(
            r.evidence["pressure_adjustment"]["source_cross_reference_printed_page"],
            298,
        )

    def test_outside_table_envelope_requires_justified_power_extrapolation(self):
        self.assertIsNone(self.cost(request(value=6000, unit="psig")).amount)
        self.assertIsNone(
            self.cost(
                request(
                    "garrett_table_linear",
                    6000,
                    "psig",
                    allow_extrapolation=True,
                    extrapolation_justification="test",
                )
            ).amount
        )
        r = self.cost(
            request(
                value=6000,
                unit="psig",
                allow_extrapolation=True,
                extrapolation_justification="Explicit unvalidated screening extension",
            )
        )
        e = r.evidence["pressure_adjustment"]
        self.assertTrue(e["extrapolated"])
        self.assertEqual(e["anchor_pressure_psi"], 5000)
        self.assertAlmostEqual(
            e["target_factor"], (5000 / 50) ** 0.44 * (6000 / 5000) ** 0.44
        )

    def test_totals_and_index_apply_once_to_all_components(self):
        native = self.cost(request())
        item = {
            "equipment_tag": "R-1",
            "curve_id": "G258-004",
            "size": 100,
            "size_unit": "gal",
            "quantity": 2,
            "costing_options": {
                "allow_unverified": True,
                "pressure_adjustment": request(),
                "target_index": 640,
                "target_period": "test",
                "target_index_source": "synthetic",
            },
        }
        r = calculate_total_cost([item])
        self.assertAlmostEqual(r.equipment_cost_total, native.equipment_cost * 4)
        self.assertAlmostEqual(r.installation_cost_total, native.installation_cost * 4)
        self.assertAlmostEqual(
            r.equipment_and_installation_cost_total,
            native.equipment_and_installation_cost * 4,
        )

    def test_parsed_design_pressure_must_match_selected_scenario(self):
        inputs = {
            "size": Measurement(100, "gal"),
            "design_pressure": Measurement(100, "barg"),
        }
        from backend.equipment_costing.unit_conversion import ConversionContext

        with self.assertRaises(UnitResolutionError):
            estimate_from_parsed_inputs(
                "G258-004",
                inputs,
                unit_context=ConversionContext(
                    input_gallon_basis="US", target_gallon_basis="US"
                ),
                pressure_adjustment=request(),
                allow_unverified=True,
            )
        inputs["design_pressure"] = Measurement(105, "barg")
        r = estimate_from_parsed_inputs(
            "G258-004",
            inputs,
            unit_context=ConversionContext(
                input_gallon_basis="US", target_gallon_basis="US"
            ),
            pressure_adjustment=request(),
            allow_unverified=True,
        )
        self.assertIsNotNone(r.amount)

    def test_dropdown_metadata_marks_proxy_and_default_unchanged(self):
        options = list_pressure_methods("G258-004")
        self.assertEqual(options[0]["id"], "native_curve")
        self.assertIn("proxy", options[1]["label"])
        self.assertEqual(len(list_pressure_methods("G258-008")), 1)
        model = next(m for m in list_equipment_models() if m["id"] == "G258-004")
        self.assertEqual(model["pressure_adjustment_options"], options)


if __name__ == "__main__":
    unittest.main()
