"""Independent workflow/ownership/research tests; no paid API calls."""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.equipment_costing.quotes import comparable_cost
from backend.equipment_costing.total_cost.calculator import calculate_total_cost
from backend.equipment_costing.unit_conversion import ConversionContext
from backend.orchestration.analyst_team import coverage_register, review_team
from backend.orchestration.commercial_pricing import adjusted_price
from backend.orchestration.deep_research import research_draft
from backend.orchestration.pipeline import run
from backend.orchestration.store import Store
from backend.orchestration.workbook_scope import calculation_scope


def entity(key, identifier, sheet, kind="material", case="", cell="B2"):
    v = {
        "id": key + ":flow",
        "property": "mass_flow",
        "component": None,
        "normalized_value": 10,
        "normalized_unit": "kg/h",
        "sheet": sheet,
        "cell": "C2",
        "original_value": 10,
        "original_unit": "kg/h",
        "status": "verified",
    }
    return {
        "key": key,
        "kind": kind,
        "identifier": identifier,
        "case": case,
        "id_evidence": dict(v, id=key + ":id", cell=cell),
        "values": [v],
        "stream_keys": [],
        "table": "table",
    }


def report():
    return {
        "entities": [
            entity("s1", "1", "Active"),
            entity("tank", "T-1", "Active", "equipment"),
            entity("reference", "1", "Old example"),
        ],
        "sheets": [{"name": x} for x in ["Active", "Supporting", "Old example"]],
        "connections": [
            {"stream_key": "s1", "equipment_key": "tank", "role": "destination"}
        ],
        "checks": [{"status": "verified"}],
    }


def decision(sheet, role, keys=None):
    return {
        "sheet": sheet,
        "role": role,
        "rationale": "Independent test",
        "needed_entity_keys": keys or [],
    }


def specialist_response():
    return {
        "summary": "Independent engineering review",
        "sheet_decisions": [],
        "questions": [],
        "findings": [
            {
                "equipment_keys": ["tank"],
                "topic": "materials",
                "requirement": "Chemical compatibility",
                "recommendation": "Investigate liner and outer shell",
                "rationale": "Different wetted and structural needs",
                "evidence_ids": ["tank:flow"],
                "alternatives": ["Unlined shell", "Lined shell"],
                "challenge": "Cleaning and corrosion data missing",
                "uncertainty": "Requires materials evidence",
                "proposed_cost_owner": "T-1 lining",
                "status": "needs_research",
            }
        ],
    }


class ScopeTests(unittest.TestCase):
    def test_reference_data_stays_out_and_original_is_unchanged(self):
        r = report()
        before = copy.deepcopy(r)
        scoped = calculation_scope(
            r, [decision("Active", "active"), decision("Old example", "reference")]
        )
        self.assertEqual({e["key"] for e in scoped["entities"]}, {"s1", "tank"})
        self.assertEqual(r, before)
        self.assertTrue(all(c["status"] == "unresolved" for c in scoped["checks"]))

    def test_duplicate_same_source_is_coalesced_and_links_remapped(self):
        r = report()
        dup = copy.deepcopy(r["entities"][0])
        dup["key"] = "dup"
        r["entities"].append(dup)
        r["connections"].append(
            {"stream_key": "dup", "equipment_key": "tank", "role": "source"}
        )
        scoped = calculation_scope(r, [decision("Active", "active")])
        self.assertEqual(len(scoped["entities"]), 2)
        self.assertEqual(scoped["calculation_scope"]["aliases"], {"dup": "s1"})
        self.assertEqual(scoped["connections"][-1]["stream_key"], "s1")

    def test_distinct_cases_not_silently_merged(self):
        r = report()
        dup = entity("othercase", "1", "Active", case="turndown")
        r["entities"].append(dup)
        s = calculation_scope(r, [decision("Active", "active")])
        self.assertEqual(len(s["entities"]), 3)

    def test_supporting_properties_only_supplement_unique_identity(self):
        r = report()
        extra = entity("support", "1", "Supporting")
        extra["values"][0].update(
            property="temperature", normalized_value=30, normalized_unit="degC"
        )
        r["entities"].append(extra)
        s = calculation_scope(
            r,
            [
                decision("Active", "active"),
                decision("Supporting", "supporting", ["support"]),
            ],
        )
        self.assertEqual(len(s["entities"]), 2)
        self.assertEqual(s["entities"][0]["values"][-1]["property"], "temperature")
        extra["values"][0].update(
            property="mass_flow", normalized_value=20, normalized_unit="kg/h"
        )
        s = calculation_scope(
            r,
            [
                decision("Active", "active"),
                decision("Supporting", "supporting", ["support"]),
            ],
        )
        self.assertEqual(len(s["entities"][0]["values"]), 1)
        self.assertTrue(s["calculation_scope"]["notes"])

    def test_invalid_scope_rejected(self):
        for choices in [
            [decision("absent", "active")],
            [decision("Active", "reference")],
            [decision("Active", "active"), decision("Active", "reference")],
        ]:
            with self.assertRaises(ValueError):
                calculation_scope(report(), choices)


class SpecialistTests(unittest.TestCase):
    def test_independent_roles_are_cached_and_ownership_disclosed(self):
        class Provider:
            model = "test"
            calls = 0

            def generate(self, **kwargs):
                self.calls += 1
                return specialist_response()

        p = Provider()
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "test.sqlite3")
            a = review_team(report(), "A chemical process", "engineering", store, p)
            b = review_team(report(), "A chemical process", "engineering", store, p)
        self.assertEqual(p.calls, 3)
        self.assertTrue(all(r["cached"] for r in b))
        self.assertEqual(len({r["role"] for r in a}), 3)
        self.assertEqual(coverage_register(a)[0]["status"], "reconcile_overlap")
        self.assertTrue(all(r["status"] == "proposed_not_approved" for r in a))

    def test_fabricated_evidence_does_not_enter_review(self):
        class Provider:
            model = "bad"

            def generate(self, **kwargs):
                r = specialist_response()
                r["findings"][0]["evidence_ids"] = ["imagined"]
                return r

        with tempfile.TemporaryDirectory() as folder:
            result = review_team(
                report(),
                "Process",
                "engineering",
                Store(Path(folder) / "test.db"),
                Provider(),
            )
        self.assertTrue(all(r["status"] == "proposed_not_approved" for r in result))
        self.assertTrue(all(r["findings"][0]["evidence_ids"] == [] for r in result))
        self.assertTrue(
            all(
                r["findings"][0]["unsupported_references"] == ["imagined"]
                for r in result
            )
        )


class PricingTests(unittest.TestCase):
    def observation(self):
        return {
            "observed_price": 100,
            "discount_fraction": 0.3,
            "observation_type": "retail_listing",
            "currency": "USD",
            "price_period": "2026",
            "quantity_unit": "kg",
            "source_url": "https://example.com/item",
            "observed_at": "2026-10-31",
            "rationale": "Explicit bulk-price scenario, not a quote",
        }

    def test_discount_is_explicit_and_basis_preserved(self):
        r = adjusted_price(
            self.observation(), currency="USD", price_period="2026", quantity_unit="kg"
        )
        self.assertEqual(r["unit_price"], 70)
        self.assertEqual(r["observed_price"], 100)
        self.assertEqual(r["status"], "user_commercial_assumption")
        with self.assertRaises(ValueError):
            adjusted_price(
                self.observation(),
                currency="USD",
                price_period="1987",
                quantity_unit="kg",
            )
        with self.assertRaises(ValueError):
            adjusted_price(
                self.observation(),
                currency="USD",
                price_period="2026",
                quantity_unit="t",
            )

    def test_no_default_discount_and_invalid_observation_rejected(self):
        o = self.observation()
        o.pop("discount_fraction")
        self.assertEqual(
            adjusted_price(o, currency="USD", price_period="2026", quantity_unit="kg")[
                "unit_price"
            ],
            100,
        )
        for bad in [1, float("nan"), -0.1]:
            o = self.observation()
            o["discount_fraction"] = bad
            with self.assertRaises(ValueError):
                adjusted_price(
                    o, currency="USD", price_period="2026", quantity_unit="kg"
                )

    def quote(self):
        return {
            "amount": 1000,
            "size": 1,
            "size_unit": "m3",
            "currency": "USD",
            "price_period": "early 1987",
            "source_url": "https://example.com/vendor",
            "same_configuration_confirmed": True,
            "cost_index": 320,
            "cost_scope": "purchased_equipment",
            "exponent": 1,
            "rationale": "Explicit synthetic size exponent",
        }

    def test_comparable_scaling_converts_units_without_escalating(self):
        q = self.quote()
        r = comparable_cost(
            q,
            target_size=2000,
            target_unit="L",
            exponent=1,
            rationale="Linear synthetic test",
        )
        self.assertEqual(r["amount"], 2000)
        self.assertFalse(r["escalation_applied"])
        self.assertEqual(r["price_period"], "early 1987")
        q["same_configuration_confirmed"] = False
        with self.assertRaises(ValueError):
            comparable_cost(
                q, target_size=2, target_unit="m3", exponent=1, rationale="test"
            )

    def test_reviewed_quote_uses_canonical_total_and_keeps_installation_unknown(self):
        r = calculate_total_cost(
            [
                {
                    "equipment_tag": "T-1",
                    "curve_id": "external:reviewed-comparable",
                    "size": 2000,
                    "size_unit": "L",
                    "external_quote": self.quote(),
                }
            ]
        )
        self.assertEqual(r.equipment_cost_total, 2000)
        self.assertIsNone(r.installation_cost_total)
        self.assertEqual(r.equipment[0].status, "provisional")


class ResearchTests(unittest.TestCase):
    def state(self):
        return {
            "parsed": {"report": report()},
            "effective_report": report(),
            "plan": {},
            "results": {"stages": {}},
        }

    def provider(self, spoof=False):
        class Provider:
            def research(self, **kwargs):
                return {
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": "A sourced candidate with missing capacity.",
                                    "annotations": [
                                        {
                                            "type": "url_citation",
                                            "url": "https://example.com/vendor",
                                            "title": "Vendor",
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                }

            def generate(self, **kwargs):
                return {
                    "summary": "Draft",
                    "candidates": [
                        {
                            "name": "Tank",
                            "kind": "supplier_listing",
                            "source_url": "https://bad.example"
                            if spoof
                            else "https://example.com/vendor",
                            "source_date": "unknown",
                            "price": None,
                            "currency": "unknown",
                            "price_period": "unknown",
                            "quantity_unit": "item",
                            "reference_size": None,
                            "size_unit": "unknown",
                            "exponent": None,
                            "formula_description": "No formula supplied",
                            "scope": "unknown",
                            "configuration": "unknown",
                            "applicability": "Needs review",
                            "uncertainty": "Capacity absent",
                        }
                    ],
                    "missing_information": ["Capacity"],
                }

        return Provider()

    def test_research_retains_sources_and_never_applies_drafts(self):
        s = self.state()
        original = copy.deepcopy(s)
        r = research_draft(s, "equipment", "tank", self.provider())
        self.assertFalse(r["plan_changed"])
        self.assertEqual(s, original)
        self.assertIsNone(r["candidates"][0]["price"])
        self.assertEqual(r["sources"][0]["url"], "https://example.com/vendor")
        with self.assertRaises(ValueError):
            research_draft(s, "equipment", "tank", self.provider(True))

    def test_no_unknown_target_or_unsourced_result(self):
        with self.assertRaises(ValueError):
            research_draft(self.state(), "equipment", "imagined", self.provider())
        p = self.provider()
        p.research = lambda **kwargs: {"output": []}
        with self.assertRaises(ValueError):
            research_draft(self.state(), "equipment", "tank", p)

class CanonicalIntegrationTests(unittest.TestCase):
    def test_lang_is_separate_screening_never_the_selected_capex(self):
        r=report();quote=PricingTests().quote()
        plan={'equipment':[{'equipment_key':'tank','external_quote':quote,'size':2,'size_unit':'m3'}],
              'capex':{'model_id':'garrett','delivery_basis':'delivered','process_type':'fluids','factor_selection':'minimum'}}
        result=run(r,'A treatment plant',plan)
        self.assertIsNotNone(result['stages']['capex']['result'])
        self.assertEqual(result['stages']['capex']['result']['purchased_equipment'],'2000.0')
        self.assertFalse(result['screening_comparisons'][0]['included_in_capex'])
        plan['capex']['model_id']='nottingham_lang'
        result=run(r,'A treatment plant',plan)
        self.assertIsNone(result['stages']['capex']['result'])
        self.assertIn('screening comparison only',result['stages']['capex']['issues'][0])

    def test_adjusted_price_flows_into_revenue_and_finance(self):
        from backend.orchestration.operating_economics import calculate_operating_study
        from backend.tests.test_operating_economics import DESCRIPTION, fixture
        r,c,capital=fixture();baseline=calculate_operating_study(r,DESCRIPTION,c,capital)
        c=copy.deepcopy(c);item=c['sales'][0]
        item['price_observation']={'observed_price':2,'discount_fraction':.25,'observation_type':'commodity_benchmark',
            'currency':capital.currency,'price_period':capital.period,'quantity_unit':item['quantity_unit'],
            'source_url':'https://example.com/test','observed_at':'2026-10-31','rationale':'Independent commercial test assumption'}
        changed=calculate_operating_study(r,DESCRIPTION,c,capital)
        self.assertNotEqual(baseline['revenue'].annual[0].sales_revenue,changed['revenue'].annual[0].sales_revenue)
        self.assertNotEqual(baseline['financial'],changed['financial'])

    def test_research_requires_consent_and_review_checks_revision(self):
        from fastapi.testclient import TestClient

        import backend.api.app as api
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'api.db')
            s=store.create({'running':False,'parsed':{'report':report()},'analyst_reviews':[], 'plan':{}},b'file')
            with patch.object(api,'store',store),TestClient(api.app,base_url='http://localhost') as client:
                response=client.post('/api/assessments/'+s['id']+'/research',json={'revision':0,'kind':'equipment','target_id':'tank','consent':False})
                self.assertEqual(response.status_code,422)
                self.assertFalse(store.get(s['id'])['running'])
                response=client.post('/api/assessments/'+s['id']+'/review-decisions',json={'revision':0,'finding_id':'imagined','decision':'agree','comment':'test'})
                self.assertEqual(response.status_code,422)
                self.assertEqual(store.get(s['id'])['revision'],0)

    def test_explicit_research_action_saves_draft_without_changing_plan(self):
        from types import SimpleNamespace

        from fastapi.testclient import TestClient

        import backend.api.app as api
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'research.db')
            initial={'running':False,'parsed':{'report':report()},'plan':{'equipment':[]},'analyst_reviews':[]}
            s=store.create(initial,b'source')
            executor=SimpleNamespace(submit=lambda job:job())
            with patch.object(api,'store',store),patch.object(api,'executor',executor),patch('backend.orchestration.provider.EngineeringProvider',return_value=ResearchTests().provider()),TestClient(api.app,base_url='http://localhost') as client:
                response=client.post('/api/assessments/'+s['id']+'/research',json={'revision':0,'kind':'equipment','target_id':'tank','consent':True})
                self.assertEqual(response.status_code,202)
                saved=store.get(s['id'])
                self.assertEqual(saved['research_job']['status'],'completed')
                self.assertFalse(saved['running'])
                self.assertEqual(saved['plan'],initial['plan'])
                self.assertFalse(saved['research_drafts'][0]['plan_changed'])

    def test_source_and_component_charges_cannot_overlap(self):
        from backend.orchestration.operating_economics import calculate_operating_study
        from backend.tests.test_operating_economics import DESCRIPTION, fixture
        r,c,capital=fixture();whole=copy.deepcopy(c['materials'][0]);component=copy.deepcopy(whole)
        component.update(id='alternate-component',property='component_mass_flow',component='Example solute')
        c['materials'].append(component)
        with self.assertRaisesRegex(ValueError,'cannot be charged twice'):
            calculate_operating_study(r,DESCRIPTION,c,capital)

    def test_scope_alternatives_do_not_remove_valid_purchase_component(self):
        item={'equipment_tag':'R-1','curve_id':'G258-008','size':100,'size_unit':'gal',
              'costing_options':{'allow_unverified':True,'unit_context':ConversionContext(input_gallon_basis='US',target_gallon_basis='US'),
                'factors':['258.module.standard','258.installation.open_tank'], 'factor_basis_confirmation':'Independent conflicting-scope test'}}
        strict=calculate_total_cost([item]);self.assertIsNone(strict.equipment_cost_total)
        item['separate_scope_conflicts']=True
        scoped=calculate_total_cost([item]);self.assertGreater(scoped.equipment_cost_total,0)
        self.assertIsNone(scoped.installation_cost_total)
        self.assertIsNone(scoped.equipment_and_installation_cost_total)
        self.assertIn('neither is applied',' '.join(scoped.equipment[0].issues))
        self.assertEqual(scoped.equipment[0].calculation.estimate.cost_scope,'purchased_equipment')

    def test_zero_separate_staffing_does_not_delete_garrett_category(self):
        from backend.orchestration.operating_economics import calculate_operating_study
        from backend.tests.test_operating_economics import DESCRIPTION, fixture
        r,c,capital=fixture();person=copy.deepcopy(c['labour'][0]);person.update(id='no-separate-supervisor',category='supervision',headcount_fte=0,rationale='Use the Garrett supervision allowance, no separate FTE')
        c['labour'].append(person)
        result=calculate_operating_study(r,DESCRIPTION,c,capital)
        self.assertTrue(any(line.id=='garrett:supervision' and line.amount>0 for line in result['opex'][1].lines))
        self.assertFalse(any(line.id=='staff:no-separate-supervisor' for line in result['opex'][1].lines))

    def test_zero_ramp_keeps_staffing_method_not_blanket_factor(self):
        from decimal import Decimal

        from backend.opex.models import Basis
        from backend.orchestration.operating_economics import _costs_for_year
        from backend.tests.test_operating_economics import fixture
        r,c,capital=fixture();person=copy.deepcopy(c['labour'][0]);person.update(id='variable-supervisor',category='supervision',headcount_fte=1,behavior='variable')
        c['labour'].append(person)
        costs,_=_costs_for_year(r,c,Basis(capital.currency,capital.period),Decimal(7536),Decimal(0),1)
        self.assertTrue(any(line.id=='staff:variable-supervisor' and line.quantity==0 for line in costs))
        self.assertFalse(any(line.id=='garrett:supervision' for line in costs))

    def test_comparable_invalid_numbers_and_missing_fields_are_explained(self):
        q=PricingTests().quote();q['amount']='not a number'
        with self.assertRaises(ValueError):comparable_cost(q,target_size=2,target_unit='m3',exponent=1,rationale='test')
        with self.assertRaises(ValueError):comparable_cost({},target_size=2,target_unit='m3',exponent=1,rationale='test')
