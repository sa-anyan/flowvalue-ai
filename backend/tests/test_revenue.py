"""Independent revenue arithmetic, evidence, review, integration and AI failure tests."""

import json
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal, localcontext
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from backend.equipment_costing.unit_conversion import Measurement
from backend.opex.models import Basis
from backend.revenue import (
    calculate_revenue,
    freeze_project,
    get_model,
    restore_project,
    review_product,
    revise_project,
    snapshot_id,
)
from backend.revenue.advisor import (
    OpenAIRevenueProvider,
    RevenueAIError,
    draft_product,
    propose_products,
)
from backend.revenue.connectors import (
    annual_revenue_base,
    financial_handoff,
    stream_from_measurement,
)
from backend.revenue.models import (
    Adjustment,
    Assumption,
    MarketStudy,
    OperatingYear,
    Product,
    ProductYear,
    RevenueProject,
    Stream,
)
from backend.revenue.persistence import save_assessment
from backend.revenue.research import research_readiness


def a(value, unit="fraction", **kwargs):
    return Assumption(
        value,
        unit,
        "Explicit synthetic example, not an industrial estimate",
        "Synthetic test fixture",
        "Unverified test case",
        as_of="2026-10-30",
        **kwargs,
    )


def fixture():
    stream = Stream(
        "S-1",
        "Product outlet",
        a(100, "kg/h"),
        ("Synthetic balance!C5",),
        "outlet",
        "Test quality",
    )
    schedule = (OperatingYear(1, a(8000, "h/year"), a(1)),)
    market = MarketStudy(
        "Test region",
        "Test grade required",
        historical_context="Unknown real market; synthetic case",
    )
    product = Product(
        "P-1",
        "Test product",
        "S-1",
        "main_product",
        "kg",
        a(1),
        a(".8"),
        "Explicit test customer specification",
        "confirmed",
        "net_fob",
        "Test GBP/kg ex-plant net price",
        (),
        (),
        market,
        (ProductYear(1, a(10, "GBP/kg"), "fraction_of_saleable", a(".5")),),
        True,
        True,
        "Synthetic review",
    )
    return RevenueProject(
        "test",
        Basis("GBP", "2026 prices"),
        (stream,),
        schedule,
        (product,),
        "Synthetic process",
        "Test region",
    )


def changed(project, **product_changes):
    return replace(project, products=(replace(project.products[0], **product_changes),))


def year_changed(project, **year_changes):
    return changed(
        project, years=(replace(project.products[0].years[0], **year_changes),)
    )


def proposal_response():
    return {
        "candidates": [
            {
                "stream_id": "S-1",
                "name": "Test product",
                "role": "main_product",
                "reasoning": "Stream could meet a known use after specification confirmation",
                "risks": ["No buyer commitment"],
                "suggestions": [
                    {
                        "field": "selling_price",
                        "value": "12",
                        "unit": "GBP/kg",
                        "rationale": "Illustrative commercial analogy only, requires user validation",
                        "reference": "",
                        "uncertainty": "Unverified LLM estimate",
                        "as_of": "2026-10-30",
                    }
                ],
            }
        ],
        "clarification_questions": ["What grade and customer acceptance apply?"],
        "market_notes": ["Demand is unknown; request permission before research"],
        "sensitivity_parameters": ["Selling price", "Quantity sold"],
    }


class FakeProvider:
    model = "test-provider-model"

    def __init__(self, response=None):
        self.response = proposal_response() if response is None else response
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class RevenueTests(unittest.TestCase):
    def test_independent_quantity_and_revenue_arithmetic(self):
        result = calculate_revenue(fixture())
        self.assertEqual(result.issues, ())
        row = result.products[0]
        self.assertEqual(row.produced_quantity, Decimal(800000))
        self.assertEqual(row.saleable_quantity, Decimal(640000))
        self.assertEqual(row.quantity_sold, Decimal(320000))
        self.assertEqual(row.unsold_saleable_quantity, Decimal(320000))
        self.assertEqual(result.annual[0].sales_revenue, Decimal(3200000))
        self.assertIn("Synthetic balance!C5", row.source_references)

    def test_multiyear_ramp_up_and_explicit_unsold_production(self):
        project = fixture()
        schedule = (
            replace(project.schedule[0], throughput_fraction=a(".5")),
            replace(project.schedule[0], year=2),
        )
        years = project.products[0].years + (
            replace(project.products[0].years[0], year=2, sales_assumption=a(".75")),
        )
        result = calculate_revenue(
            replace(changed(project, years=years), schedule=schedule)
        )
        self.assertFalse(result.issues)
        self.assertEqual(
            tuple(y.sales_revenue for y in result.annual),
            (Decimal(1600000), Decimal(4800000)),
        )

    def test_byproducts_separate_and_allocation_blocks_duplicate_sales(self):
        project = fixture()
        main = replace(project.products[0], allocation_fraction=a(".75"))
        byproduct = replace(
            main,
            id="P-2",
            name="Byproduct",
            role="byproduct",
            allocation_fraction=a(".25"),
            years=(replace(main.years[0], selling_price=a(2, "GBP/kg")),),
        )
        result = calculate_revenue(replace(project, products=(main, byproduct)))
        self.assertEqual(result.annual[0].sales_revenue, Decimal(2560000))
        duplicate = calculate_revenue(
            replace(project, products=(project.products[0], byproduct))
        )
        self.assertFalse(duplicate.annual)
        self.assertTrue(any("allocations exceed" in i for i in duplicate.issues))

    def test_outlets_not_automatically_sold(self):
        project = fixture()
        extra = replace(project.streams[0], id="waste")
        result = calculate_revenue(replace(project, streams=project.streams + (extra,)))
        self.assertEqual(result.annual[0].sales_revenue, Decimal(3200000))
        self.assertTrue(any("not counted" in w for w in result.warnings))
        self.assertTrue(calculate_revenue(replace(project, products=())).issues)

    def test_specifications_missing_stream_and_physical_llm_data_blocked(self):
        for edits in (
            {"specification_status": "requires_review"},
            {"stream_id": "invented"},
            {"specification_basis": ""},
            {"role": "waste_is_always_a_sale"},
        ):
            self.assertTrue(calculate_revenue(changed(fixture(), **edits)).issues)
        project = fixture()
        for stream in (
            replace(project.streams[0], boundary="internal"),
            replace(project.streams[0], flow=a(100, "kg/h", status="llm_estimate")),
        ):
            self.assertTrue(
                calculate_revenue(replace(project, streams=(stream,))).issues
            )

    def test_review_and_exclusions(self):
        project = changed(fixture(), reviewed=False)
        self.assertTrue(calculate_revenue(project).issues)
        self.assertEqual(
            calculate_revenue(project, preview=True).annual[0].sales_revenue,
            Decimal(3200000),
        )
        self.assertEqual(
            calculate_revenue(project, preview=True).status, "draft_preview"
        )
        excluded = changed(
            fixture(), included=False, exclusion_reason="Not saleable in this scenario"
        )
        self.assertEqual(calculate_revenue(excluded).annual[0].sales_revenue, 0)
        self.assertTrue(
            calculate_revenue(changed(excluded, exclusion_reason="")).issues
        )

    def test_net_fob_deductions_premiums_and_no_compounding(self):
        project = changed(fixture(), additional_charge_scopes=("freight", "discount"))
        premium = Adjustment(
            "premium", "quality_premium", "premium", "per_unit", a(2, "GBP/kg")
        )
        freight = Adjustment(
            "freight", "freight", "deduction", "per_unit", a(1, "GBP/kg")
        )
        discount = Adjustment(
            "discount", "discount", "deduction", "fraction_of_quote", a(".1")
        )
        result = calculate_revenue(
            year_changed(project, adjustments=(premium, freight, discount))
        )
        self.assertFalse(result.issues)
        self.assertEqual(result.products[0].net_selling_price, Decimal(10))
        self.assertEqual(result.annual[0].sales_revenue, Decimal(3200000))

    def test_included_freight_not_deducted_twice(self):
        freight = Adjustment(
            "freight", "freight", "deduction", "per_unit", a(1, "GBP/kg")
        )
        project = changed(fixture(), included_charges=("freight",))
        bad = calculate_revenue(year_changed(project, adjustments=(freight,)))
        self.assertTrue(any("already included" in i for i in bad.issues))
        annotated = replace(freight, accounting="included_in_quote")
        self.assertEqual(
            calculate_revenue(year_changed(project, adjustments=(annotated,)))
            .annual[0]
            .sales_revenue,
            Decimal(3200000),
        )

    def test_opex_classification_never_reduces_revenue_and_deduction_needs_scope(self):
        freight = Adjustment(
            "freight", "freight", "deduction", "per_unit", a(1, "GBP/kg"), "opex"
        )
        self.assertTrue(
            calculate_revenue(year_changed(fixture(), adjustments=(freight,))).issues
        )
        result = calculate_revenue(
            year_changed(
                changed(fixture(), additional_charge_scopes=("freight",)),
                adjustments=(freight,),
            )
        )
        self.assertEqual(result.annual[0].sales_revenue, Decimal(3200000))
        self.assertEqual(result.annual[0].separate_opex_charges, Decimal(320000))
        self.assertEqual(
            financial_handoff(result)["unapplied_opex_charges"][0][-1], Decimal(320000)
        )

    def test_duplicate_and_hierarchical_adjustments_negative_price(self):
        project = changed(
            fixture(), additional_charge_scopes=("freight", "freight:outbound")
        )
        adjustment = Adjustment(
            "freight", "freight", "deduction", "per_unit", a(1, "GBP/kg")
        )
        for adjustments in (
            (adjustment, adjustment),
            (
                adjustment,
                replace(adjustment, id="second", cost_scope="freight:outbound"),
            ),
            (replace(adjustment, assumption=a(11, "GBP/kg")),),
        ):
            self.assertTrue(
                calculate_revenue(year_changed(project, adjustments=adjustments)).issues
            )

    def test_market_share_and_growth_are_explicit_and_10_percent_not_cap(self):
        project = fixture()
        market = replace(
            project.products[0].market,
            base_demand=a(1000000, "kg/year"),
            annual_growth=a(".1", "fraction/year"),
            reference="Synthetic commercial assumption",
        )
        project = year_changed(
            changed(project, market=market),
            sales_method="market_share",
            sales_assumption=a(".2"),
        )
        result = calculate_revenue(project)
        self.assertFalse(result.issues)
        self.assertEqual(result.products[0].quantity_sold, Decimal(200000))
        self.assertTrue(any("10%" in w for w in result.warnings))
        self.assertTrue(
            calculate_revenue(
                year_changed(
                    fixture(), sales_method="market_share", sales_assumption=a(".1")
                )
            ).issues
        )
        market = replace(market, annual_growth=a("-.2", "fraction/year"), base_year=1)
        project = changed(
            project,
            market=market,
            years=(replace(project.products[0].years[0], year=2),),
        )
        project = replace(project, schedule=(replace(project.schedule[0], year=2),))
        self.assertEqual(
            calculate_revenue(project).products[0].market_demand, Decimal(800000)
        )

    def test_sales_cannot_exceed_production_or_market(self):
        project = fixture()
        self.assertTrue(
            calculate_revenue(
                year_changed(
                    project,
                    sales_method="explicit_quantity",
                    sales_assumption=a(700000, "kg/year"),
                )
            ).issues
        )
        result = calculate_revenue(
            year_changed(
                project,
                sales_method="explicit_quantity",
                sales_assumption=a(50000, "kg/year"),
            )
        )
        self.assertEqual(result.annual[0].sales_revenue, Decimal(500000))
        market = replace(
            project.products[0].market,
            base_demand=a(1, "kg/year"),
            annual_growth=a(0, "fraction/year"),
        )
        self.assertTrue(calculate_revenue(changed(project, market=market)).issues)

    def test_unit_conversion_and_unsupported_mass_volume(self):
        project = fixture()
        grams = replace(project.streams[0], flow=a(100000, "g/h"))
        self.assertEqual(
            calculate_revenue(replace(project, streams=(grams,)))
            .annual[0]
            .sales_revenue,
            Decimal(3200000),
        )
        volume = replace(project.streams[0], flow=a(100, "m3/h"))
        self.assertTrue(calculate_revenue(replace(project, streams=(volume,))).issues)
        self.assertTrue(
            calculate_revenue(
                year_changed(project, selling_price=a(10, "USD/kg"))
            ).issues
        )

    def test_missing_numeric_and_metadata_bounds(self):
        project = fixture()
        for price in (
            a(None, "GBP/kg"),
            a(-1, "GBP/kg"),
            replace(a(10, "GBP/kg"), as_of=""),
            replace(a(10, "GBP/kg"), rationale=""),
        ):
            self.assertTrue(
                calculate_revenue(year_changed(project, selling_price=price)).issues
            )
        self.assertTrue(
            calculate_revenue(changed(project, saleable_fraction=a("1.1"))).issues
        )
        schedule = (replace(project.schedule[0], operating_hours=a(9000, "h/year")),)
        self.assertTrue(calculate_revenue(replace(project, schedule=schedule)).issues)
        for value in (True, "NaN", "Infinity", "invalid"):
            with self.assertRaises((ValueError, TypeError)):
                a(value)

    def test_duplicate_ids_and_mismatched_years(self):
        project = fixture()
        for modified in (
            replace(project, streams=project.streams * 2),
            replace(project, products=project.products * 2),
            replace(project, schedule=project.schedule * 2),
            changed(project, years=()),
        ):
            self.assertTrue(calculate_revenue(modified).issues)
        with self.assertRaises(ValueError):
            get_model("not_implemented")

    def test_zero_sales_is_not_unknown_and_zero_output_year(self):
        result = calculate_revenue(year_changed(fixture(), sales_assumption=a(0)))
        self.assertFalse(result.issues)
        self.assertEqual(result.annual[0].sales_revenue, 0)
        project = fixture()
        project = replace(
            project,
            schedule=(replace(project.schedule[0], operating_hours=a(0, "h/year")),),
        )
        self.assertEqual(calculate_revenue(project).annual[0].sales_revenue, 0)

    def test_saved_overrides_recalculate_without_model_call(self):
        baseline = fixture()
        altered = replace(
            baseline.products[0],
            years=(
                replace(baseline.products[0].years[0], selling_price=a(12, "GBP/kg")),
            ),
        )
        updated = revise_project(
            baseline,
            actor="user",
            reason="Price sensitivity",
            expected_snapshot_id=snapshot_id(baseline),
            products=(altered,),
        )
        with patch(
            "backend.revenue.advisor.propose_products",
            side_effect=AssertionError("No AI calls"),
        ):
            preview = calculate_revenue(updated, preview=True)
            self.assertEqual(preview.annual[0].sales_revenue, Decimal(3840000))
        reviewed = review_product(
            updated,
            "P-1",
            actor="user",
            reason="Reviewed new price",
            expected_snapshot_id=snapshot_id(updated),
        )
        self.assertEqual(
            calculate_revenue(reviewed).annual[0].sales_revenue, Decimal(3840000)
        )
        self.assertEqual(
            calculate_revenue(baseline).annual[0].sales_revenue, Decimal(3200000)
        )
        self.assertEqual(restore_project(freeze_project(reviewed)), reviewed)
        with self.assertRaises(ValueError):
            revise_project(
                baseline, actor="user", reason="edit", expected_snapshot_id="stale"
            )
        with self.assertRaises(FrozenInstanceError):
            baseline.products[0].reviewed = False

    def test_saved_input_results_and_opex_adapter(self):
        project = fixture()
        result = calculate_revenue(project)
        self.assertEqual(annual_revenue_base(result, 1).amount, Decimal(3200000))
        with self.assertRaises(ValueError):
            annual_revenue_base(calculate_revenue(project, preview=True), 1)
        with tempfile.TemporaryDirectory() as folder:
            path = save_assessment(project, result, Path(folder) / "assessment.json")
            saved = json.loads(path.read_text())
            restored = restore_project(json.dumps(saved["input_snapshot"]))
            self.assertEqual(calculate_revenue(restored), result)
            with self.assertRaises(FileExistsError):
                save_assessment(project, result, path)
            with self.assertRaises(ValueError):
                save_assessment(
                    changed(project, name="changed"),
                    result,
                    Path(folder) / "stale.json",
                )

    def test_canonical_measurement_bridge_and_no_raw_parser_changes(self):
        stream = stream_from_measurement(
            stream_id="out",
            name="Product",
            measurement=Measurement(100, "kg/h", {"sheet": "Balance", "cell": "C5"}),
            evidence={
                "rationale": "Parsed",
                "source": "workbook",
                "uncertainty": "Unverified",
                "as_of": "2026-10-30",
            },
        )
        self.assertEqual(stream.boundary, "unresolved")
        self.assertIn("C5", stream.source_references[0])
        with self.assertRaises(ValueError):
            stream_from_measurement(
                stream_id="out",
                name="Product",
                measurement=Measurement(100, "kg/h"),
                evidence={},
            )

    def test_decimal_context_independence(self):
        project = fixture()
        expected = calculate_revenue(project)
        with localcontext() as context:
            context.prec = 3
            self.assertEqual(calculate_revenue(project), expected)

    def test_llm_physical_fractions_require_user_engineering_resolution(self):
        self.assertTrue(
            calculate_revenue(
                changed(fixture(), allocation_fraction=a(1, status="llm_estimate"))
            ).issues
        )
        self.assertTrue(
            calculate_revenue(
                changed(fixture(), saleable_fraction=a(".8", status="llm_estimate"))
            ).issues
        )

    def test_justified_premium_is_not_artificially_limited_to_100_percent(self):
        premium = Adjustment(
            "grade", "new_grade_premium", "premium", "fraction_of_quote", a(2)
        )
        result = calculate_revenue(year_changed(fixture(), adjustments=(premium,)))
        self.assertEqual(result.products[0].net_selling_price, Decimal(30))


class RevenueAdvisorTests(unittest.TestCase):
    def test_explicit_model_call_draft_and_stale_proposal(self):
        project = fixture()
        provider = FakeProvider()
        with self.assertRaises(PermissionError):
            propose_products(project, provider)
        self.assertEqual(provider.calls, [])
        proposal = propose_products(project, provider, allow_model_call=True)
        self.assertEqual(proposal.status, "unreviewed_llm_proposal")
        self.assertEqual(
            proposal.candidates[0].suggestions[0].assumption.status, "llm_estimate"
        )
        product = draft_product(
            project, proposal, 0, product_id="candidate", quantity_unit="kg"
        )
        self.assertFalse(product.reviewed)
        self.assertIsNone(product.allocation_fraction.value)
        self.assertEqual(product.specification_status, "requires_review")
        self.assertTrue(
            calculate_revenue(
                replace(project, products=(product,)), preview=True
            ).issues
        )
        with self.assertRaises(ValueError):
            draft_product(
                changed(project, name="new"),
                proposal,
                0,
                product_id="candidate",
                quantity_unit="kg",
            )

    def test_invented_stream_sources_and_contract_probability_rejected(self):
        for mutation in ("stream", "source", "probability", "percent"):
            response = proposal_response()
            if mutation == "stream":
                response["candidates"][0]["stream_id"] = "invented"
            elif mutation == "source":
                response["candidates"][0]["suggestions"][0]["reference"] = (
                    "https://fabricated.example/quote"
                )
            elif mutation == "probability":
                response["contract_probability"] = ".9"
            else:
                response["candidates"][0]["suggestions"][0].update(
                    field="sales_fraction", value="25", unit="fraction"
                )
            with self.assertRaises(ValueError):
                propose_products(
                    fixture(), FakeProvider(response), allow_model_call=True
                )

    def test_unknown_price_stays_unknown_and_research_permission_no_calls(self):
        response = proposal_response()
        response["candidates"][0]["suggestions"][0]["value"] = None
        proposal = propose_products(
            fixture(), FakeProvider(response), allow_model_call=True
        )
        self.assertIsNone(proposal.candidates[0].suggestions[0].assumption.value)
        self.assertEqual(research_readiness(permission=None), "permission_required")
        self.assertEqual(research_readiness(permission=False), "declined")
        self.assertEqual(
            research_readiness(permission=True, consent_reference="user approved"),
            "ready_for_future_connector",
        )

    def test_provider_disabled_and_sanitized_network_error(self):
        with (
            patch.dict("os.environ", {}, clear=True),
            self.assertRaises(RevenueAIError),
        ):
            OpenAIRevenueProvider.from_environment()
        provider = OpenAIRevenueProvider(
            api_key="test-secret-never-print", model="configured-model"
        )
        with patch("backend.revenue.advisor.build_opener") as opener:
            opener.return_value.open.side_effect = URLError("test-secret-never-print")
            with self.assertRaises(RevenueAIError) as caught:
                provider.generate(instructions="test", context={}, schema={})
            self.assertNotIn("test-secret", str(caught.exception))

    def test_provider_structured_payload_refusal_incomplete_and_malformed(self):
        provider = OpenAIRevenueProvider(api_key="test-key", model="configured-model")
        completed = {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": json.dumps(proposal_response())}
                    ],
                }
            ],
        }
        with patch("backend.revenue.advisor.build_opener") as opener:
            response = opener.return_value.open.return_value.__enter__.return_value
            response.read.return_value = json.dumps(completed).encode()
            output = provider.generate(instructions="test", context={}, schema={})
            self.assertEqual(output, proposal_response())
            request = opener.return_value.open.call_args.args[0]
            payload = json.loads(request.data)
            self.assertFalse(payload["store"])
            self.assertNotIn("tools", payload)
            self.assertTrue(payload["text"]["format"]["strict"])
            for bad in (
                [],
                {"status": "completed", "output": ["malformed"]},
                {"status": "incomplete"},
                {
                    "status": "completed",
                    "output": [{"type": "message", "content": [{"type": "refusal"}]}],
                },
                {"status": "completed", "output": []},
            ):
                response.read.return_value = json.dumps(bad).encode()
                with self.assertRaises(RevenueAIError):
                    provider.generate(instructions="test", context={}, schema={})


if __name__ == "__main__":
    unittest.main()
