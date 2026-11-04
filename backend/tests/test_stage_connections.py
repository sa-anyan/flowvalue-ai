"""Real parser → costing → economics → finance, with complete explicit test inputs.

No provider calls, production assessments, source study prices or mock engines.
"""

import copy
import json
import socket
import tempfile
import unittest
from decimal import Decimal as D
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import openpyxl

from backend.ingestion.balance.models import BalanceReport
from backend.orchestration.ingest import parse
from backend.orchestration.service import edit, execute, new_assessment
from backend.orchestration.sizing import derive_size
from backend.orchestration.store import Store
from backend.orchestration.workbook_review import apply_review
from backend.tests.test_engineering_review import fixture as review_fixture, response
from backend.tests.test_operating_economics import fixture

MARK = "SYNTHETIC_ARCHITECTURE_TEST"
DESCRIPTION = "Continuous water treatment; this test sells treated water."


def workbook():
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Balance"
    sheet.append(
        [
            "Stream ID",
            "Description",
            "Mass flow (kg/h)",
            "Temperature (C)",
            "Pressure (bar)",
        ]
    )
    sheet.append(["S-101", "Water entering Storage Tank T-101", 1000, 25, 1])
    sheet.append(["S-102", "Water leaving Storage Tank T-101", 800, 25, 1])
    data = BytesIO()
    book.save(data)
    return data.getvalue()


def plan_for(report):
    _, config, _ = fixture()
    streams = {
        e["identifier"]: e for e in report["entities"] if e["kind"] == "material"
    }
    tank = next(e for e in report["entities"] if e["kind"] == "equipment")
    config["origin"] = MARK
    config["financial"].update(
        operating_years=20, production_ramp=[1] * 20, depreciation_years=20
    )
    config["sales"][0].update(
        stream_key=streams["S-102"]["key"],
        quantity_unit="kg",
        saleable_fraction=1,
        sold_fraction=1,
    )
    config["materials"][0].update(stream_key=streams["S-101"]["key"])
    config["energy"][0].update(equipment_key=tank["key"])
    config["garrett_factors"]["maintenance"].update(
        fraction=1, override=True, override_reason=MARK
    )
    return {
        "equipment": [
            {
                "equipment_key": tank["key"],
                "curve_id": "G303-144",
                "quantity": 2,
                "sizing": {
                    "method": "vessel_hold_up",
                    "stream_key": streams["S-101"]["key"],
                    "parameters": {
                        "density_kg_m3": {
                            "value": 1000,
                            "unit": "kg/m3",
                            "source": MARK,
                        },
                        "residence_time_h": {"value": 24, "unit": "h", "source": MARK},
                        "working_fraction": {
                            "value": 1,
                            "unit": "fraction",
                            "source": MARK,
                        },
                    },
                },
                "costing_options": {
                    "allow_unverified": True,
                    "unit_context": {"target_gallon_basis": "US"},
                },
                "rationale": MARK
                + "; two explicitly supplied physical units, not inferred from AB",
            }
        ],
        "capex": {
            "model_id": "garrett",
            "delivery_basis": "delivered",
            "process_type": "mixed",
            "factor_selection": "minimum",
        },
        "operating_economics": config,
        "cost_translation": {"enabled": False},
    }


class StageConnectionTests(unittest.TestCase):
    def test_review_source_ids_survive_sorted_json(self):
        source, decision = review_fixture(), response()
        a, _ = apply_review(source, decision)
        b, _ = apply_review(
            json.loads(json.dumps(source, sort_keys=True)),
            json.loads(json.dumps(decision, sort_keys=True)),
        )
        self.assertEqual(a, b)

    def test_scalar_and_typed_sizing_parameters_share_one_calculation(self):
        report = {
            "entities": [
                {
                    "key": "feed",
                    "values": [
                        {
                            "id": "flow",
                            "property": "mass_flow",
                            "normalized_value": 1000,
                            "normalized_unit": "kg/h",
                            "status": "verified",
                        }
                    ],
                }
            ]
        }
        typed = {
            "method": "vessel_hold_up",
            "stream_key": "feed",
            "parameters": {
                "density_kg_m3": {"value": 1000, "unit": "kg/m3"},
                "residence_time_h": {"value": 2, "unit": "h"},
                "working_fraction": {"value": 1, "unit": "fraction"},
            },
        }
        scalar = copy.deepcopy(typed)
        scalar["parameters"] = {k: v["value"] for k, v in typed["parameters"].items()}
        a, b = derive_size({"sizing": typed}, report), derive_size(
            {"sizing": scalar}, report
        )
        self.assertEqual(a[:2], (2, "m3"))
        self.assertEqual(a[:2], b[:2])
        self.assertEqual(a[2]["source_evidence"], b[2]["source_evidence"])

    def test_saved_edits_recalculate_every_stage_without_ai(self):
        data = workbook()
        with tempfile.TemporaryDirectory() as folder, patch.object(
            socket.socket, "connect", side_effect=AssertionError("No network")
        ), patch(
            "backend.orchestration.service.propose", side_effect=AssertionError("No AI")
        ):
            store = Store(Path(folder) / "test.db")
            state = new_assessment(store, data, "synthetic-balance.xlsx", DESCRIPTION)
            parsed = parse(data, state["filename"])
            # No extra-field workaround: the parser output is the canonical contract.
            BalanceReport.model_validate(parsed["report"])
            self.assertEqual(
                sum(e["kind"] == "equipment" for e in parsed["report"]["entities"]), 1
            )
            state.update(parsed=parsed, plan=plan_for(parsed["report"]), running=False)
            state = store.put(state, state["revision"])
            a = execute(store, state["id"], use_ai=False)
            self.check_connected(a)
            baseline = store.version(state["id"], "Baseline")
            # Change supplied hold-up: real sizing and cost model must both rerun.
            items = copy.deepcopy(a["plan"]["equipment"])
            items[0]["sizing"]["parameters"]["residence_time_h"]["value"] = 48
            edit(store, state["id"], a["revision"], "equipment", items, MARK)
            b = execute(store, state["id"], use_ai=False)
            self.check_connected(b)
            self.assertGreater(self.capex(b), self.capex(a))
            self.assertGreater(self.opex(b)["cash_fixed"], self.opex(a)["cash_fixed"])
            self.assertNotEqual(self.npv(a), self.npv(b))
            # Change utilisation, preserving all original observed flow values.
            config = copy.deepcopy(b["plan"]["operating_economics"])
            config["operating"]["days_per_year"] /= 2
            edit(store, state["id"], b["revision"], "operating_economics", config, MARK)
            c = execute(store, state["id"], use_ai=False)
            self.check_connected(c)
            self.assertEqual(self.capex(c), self.capex(b))
            self.assertEqual(self.opex(c)["cash_fixed"], self.opex(b)["cash_fixed"])
            self.assertEqual(
                D(self.opex(c)["cash_variable"]) * 2, D(self.opex(b)["cash_variable"])
            )
            self.assertEqual(
                D(self.result(c, "revenue")["annual"][0]["sales_revenue"]) * 2,
                D(self.result(b, "revenue")["annual"][0]["sales_revenue"]),
            )
            self.assertNotEqual(self.npv(c), self.npv(b))
            # Saved user values, source cells and baseline are retained on replay.
            replay = execute(store, state["id"], use_ai=False)
            self.assertEqual(c["results"], replay["results"])
            self.assertEqual(store.load(baseline)["results"], a["results"])
            self.assertEqual(c["parsed"], a["parsed"])
            self.assertEqual(c["plan"]["equipment"], items)

    def result(self, state, stage):
        return state["results"]["stages"][stage]["result"]

    def capex(self, state):
        return D(self.result(state, "capex")["total_capex"])

    def opex(self, state):
        return self.result(state, "opex")["years"]["1"]

    def npv(self, state):
        return D(
            dict(self.result(state, "financial")["metrics"])["project_npv"]["value"]
        )

    def check_connected(self, state):
        self.assertNotEqual(state.get("status"), "failed", state.get("error"))
        for name in (
            "equipment",
            "capex",
            "operating_economics",
            "opex",
            "revenue",
            "financial",
        ):
            stage = state["results"]["stages"][name]
            self.assertNotIn(
                stage["status"],
                ("pending", "partial", "unresolved", "pending_dependencies"),
                stage,
            )
            self.assertIsNotNone(stage["result"])
        costs = self.result(state, "equipment")
        self.assertEqual(len(costs["equipment"]), 1)
        item = costs["equipment"][0]
        self.assertEqual(item["quantity"], 2)
        self.assertAlmostEqual(
            float(self.result(state, "capex")["purchased_equipment"]),
            item["equipment_cost"],
        )
        op = self.opex(state)
        maintenance = next(x for x in op["lines"] if x["category"] == "maintenance")
        self.assertEqual(maintenance["override_reason"], MARK)
        self.assertEqual(maintenance["amount"], maintenance["base_amount"])
        f = self.result(state, "financial")
        self.assertEqual(len(f["ledger"]), 22)
        rows = [x for x in f["ledger"] if x["products"]]
        self.assertEqual(len(rows), 20)
        for year, row in enumerate(rows, 1):
            opex = self.result(state, "opex")["years"][str(year)]
            revenue = self.result(state, "revenue")["annual"][year - 1]
            self.assertEqual(row["fixed_opex"], opex["cash_fixed"])
            self.assertEqual(row["variable_opex"], opex["cash_variable"])
            self.assertEqual(row["revenue"], revenue["sales_revenue"])
