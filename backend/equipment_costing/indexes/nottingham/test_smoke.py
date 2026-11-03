"""Three focused integration checks; run with python -m unittest backend.equipment_costing.indexes.nottingham.test_smoke."""
import unittest

from backend.equipment_costing.registry import estimate_cost, list_equipment_models
from backend.equipment_costing.total_cost.calculator import calculate_total_cost


class NottinghamSmokeTest(unittest.TestCase):
    def test_catalogue_has_both_sources(self):
        models = list_equipment_models(source="all")
        self.assertTrue(any(m["id"].startswith("G") for m in models))
        self.assertTrue(any(m["id"] == "N501-PUMP-CAST_STEEL" for m in models))

    def test_published_equation_historical_cost(self):
        result = estimate_cost("N501-PUMP-CAST_STEEL", 5, source="nottingham", size_unit="kW")
        self.assertAlmostEqual(result.amount, 2000 * 1.5 * (5 ** .7))
        self.assertEqual(result.estimate.currency, "GBP")
        self.assertEqual(result.estimate.period, "2015")
        self.assertIsNone(result.installation_cost)

    def test_pipeline_translation_and_fx(self):
        total = calculate_total_cost(
            [{"equipment_tag": "P-TEST", "curve_id": "N501-PUMP-CAST_STEEL",
              "source": "nottingham", "size": 5, "size_unit": "kW", "quantity": 1}],
            translation_policy={"target_period": "2026-09", "allow_general_inflation_proxy": True},
        )
        line = total.equipment[0]
        self.assertIsNotNone(line.amount)
        self.assertEqual(line.calculation.estimate.currency, "USD")
        self.assertEqual(line.calculation.estimate.period, "2026-09")
        self.assertIn("cost_translation", line.calculation.evidence)
        self.assertIn("currency_conversion", line.calculation.evidence)


if __name__ == "__main__":
    unittest.main()
