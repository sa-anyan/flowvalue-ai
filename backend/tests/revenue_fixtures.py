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
    config["sales"][0]["intent_id"] = "sale"
    config["commercial_intent"] = {
        "status": "explicit",
        "mechanisms": [
            {
                "id": "sale",
                "category": "product_sales",
                "context_quote": "sells treated water",
                "interpretation": MARK,
            }
        ],
        "questions": [],
    }
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
