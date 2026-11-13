"""P2 G2 independent arithmetic: actual financial engine mutation fixture.

Uses the existing synthetic finance fixture and independent cashflow arithmetic.
This is a finance-stage numerical check, NOT full Engineering-to-Finance G2.
"""
import unittest
from decimal import Decimal as D

from backend.financial_modelling import calculate_financials
from backend.tests.test_financial_modelling import fixture, metric


class G2FinancialMutationTests(unittest.TestCase):
    def test_revenue_mutation_recalculates_real_ledger_and_npv(self):
        baseline = calculate_financials(fixture(revenue=80))
        changed = calculate_financials(fixture(revenue=100))
        self.assertFalse(baseline.issues, baseline.issues)
        self.assertFalse(changed.issues, changed.issues)
        self.assertEqual(tuple(row.fcff for row in baseline.ledger),
                         (D(-110), D(50), D(60)))
        # Annual sales increase 20; taxable profit rises from 0 to 20.
        # Synthetic 25% tax yields incremental annual after-tax cash 15.
        self.assertEqual(tuple(row.fcff for row in changed.ledger),
                         (D(-110), D(65), D(75)))
        expected_base = D(-110) + D(50) / D("1.1") + D(60) / D("1.21")
        expected_changed = D(-110) + D(65) / D("1.1") + D(75) / D("1.21")
        self.assertAlmostEqual(metric(baseline, "project_npv").value,
                               expected_base, places=20)
        self.assertAlmostEqual(metric(changed, "project_npv").value,
                               expected_changed, places=20)
        self.assertAlmostEqual(
            metric(changed, "project_npv").value -
            metric(baseline, "project_npv").value,
            D(15) / D("1.1") + D(15) / D("1.21"), places=20,
        )
        self.assertEqual(tuple(row.capex for row in changed.ledger),
                         tuple(row.capex for row in baseline.ledger))
        self.assertEqual(tuple(row.depreciation for row in changed.ledger),
                         tuple(row.depreciation for row in baseline.ledger))


if __name__ == "__main__":
    unittest.main()
