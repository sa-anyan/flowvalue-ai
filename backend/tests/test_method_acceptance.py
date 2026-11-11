"""METHOD-001: only new source/physical-reference and trace-propagation coverage."""

import ast
import copy
import json
from pathlib import Path
import pytest
from backend.engineering_sizing import calculate
from backend.equipment_costing.unit_conversion import convert, identify_unit
from backend.equipment_costing.unit_conversion.bridges import (
    mechanical,
    production_sizing,
    liquid,
)

ROOT = Path(__file__).resolve().parents[2]
REFS = json.loads(
    (
        ROOT
        / "docs/verification/phase1/method_acceptance/evidence/additional_references.json"
    ).read_text()
)


def cv(value, unit, target=None):
    if value == "quantity":
        return identify_unit(unit).quantity
    r = convert(value, unit, target)
    if r.value is None:
        raise ValueError("; ".join(r.issues))
    return r.value


def evaluate_reference(c):
    if c["method"] == "vessel_mass":
        return mechanical.evaluate(c["inputs"])
    if c["method"] == "vessel_productivity":
        return production_sizing.vessel_productivity(c["inputs"])
    if c["method"] == "mixing_power":
        return liquid.evaluate(
            "mixing_power", c["value"], c["source_unit"], c["inputs"], cv
        )
    if c["method"] in {"mass_residence", "volume_residence"}:
        from backend.orchestration.sizing import derive_size

        prop = "mass_flow" if c["method"] == "mass_residence" else "volume_flow"
        report = {
            "entities": [
                {
                    "key": "s",
                    "values": [
                        {
                            "id": "legacy-ref",
                            "property": prop,
                            "normalized_value": c["value"],
                            "normalized_unit": c["source_unit"],
                            "status": "verified",
                        }
                    ],
                }
            ]
        }
        return derive_size(
            {"sizing": {"method": c["method"], "stream_key": "s", **c["inputs"]}},
            report,
        )
    return calculate(c["method"], c["value"], c["inputs"])


@pytest.mark.parametrize("case", REFS, ids=lambda x: x["id"])
def test_additional_independent_engineering_references(case):
    before = copy.deepcopy(case)
    value, unit, _ = evaluate_reference(case)
    assert unit == case["unit"]
    assert value == pytest.approx(
        float(case["expected"]), rel=case["rtol"], abs=case["atol"]
    )
    assert case == before


@pytest.mark.parametrize(
    "case", [x for x in REFS if x["method"] == "gas_compression"], ids=lambda x: x["id"]
)
def test_compressor_approximation_warnings_propagate_through_existing_adapter(case):
    from backend.orchestration.sizing import derive_size

    report = {
        "entities": [
            {
                "key": "s",
                "kind": "material",
                "values": [
                    {
                        "id": "METHOD-001!B3",
                        "property": "mass_flow",
                        "normalized_value": case["value"],
                        "normalized_unit": "kg/h",
                        "status": "verified",
                    }
                ],
            }
        ]
    }
    proposal = {
        "sizing": {
            "method": "gas_compression",
            "stream_key": "s",
            "parameters": copy.deepcopy(case["inputs"]),
        }
    }
    _, _, audit = derive_size(proposal, report)
    assert audit["source_evidence"] == ["METHOD-001!B3"]
    warnings = audit["calculation"]["applicability_warnings"]
    assert len(warnings) == 3
    assert any("representative" in x and "inlet Z" in x for x in warnings)
    assert any("EOS/enthalpy" in x for x in warnings)
    assert any("not a certified operating envelope" in x for x in warnings)
    assert "no condensation/intercooling" in audit["calculation"]["scope"]


def test_compressor_equation_unchanged_by_applicability_annotation():
    # Compare the pre-task AST, excluding only the descriptive return dictionary.
    before = (
        ROOT
        / "docs/verification/phase1/method_acceptance/evidence/compression_before.py.txt"
    )
    current = ROOT / "backend/engineering_sizing/compression.py"

    def arithmetic(path):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple):
                node.value.elts = node.value.elts[:2]
        return ast.dump(tree, include_attributes=False)

    assert arithmetic(before) == arithmetic(current)


def test_mixing_power_reports_the_actual_design_volume_basis():
    case = next(c for c in REFS if c["method"] == "mixing_power")
    _, _, audit = evaluate_reference(case)
    assert "Gross/design" in audit["volume_basis"]
    assert (
        "Working-volume power density needs a separate basis conversion"
        in audit["scope"]
    )
