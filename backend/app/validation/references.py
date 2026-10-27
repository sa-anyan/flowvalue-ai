"""Compare documented, frozen hand-calculated references with current engines."""

import json
from datetime import UTC, datetime
from importlib.resources import files
from math import isclose

from app.engine.costing import CostingRequest, build_bom
from app.financial.dcf_model import FinancialInputs, calculate_dcf


def reference_report() -> dict:
    catalog = json.loads(
        files("app.data").joinpath("engineering_reference_cases.json").read_text()
    )
    results = []
    for case in catalog["cases"]:
        if case["engine"] == "equipment":
            bom = build_bom(
                CostingRequest.model_validate(
                    {
                        "equipment": [case["equipment"]],
                        "settings": case.get("settings", {}),
                    }
                )
            )
            item = bom.items[0]
            actual = {
                **item.sizing,
                "base_purchase_cost_usd": item.base_purchase_cost_usd,
                "total_bare_module_cost_usd": bom.total_bare_module_cost_usd,
            }
        else:
            actual = calculate_dcf(
                FinancialInputs.model_validate(case["financial"])
            ).model_dump()
        metrics = [
            {
                "metric": name,
                "expected": expected,
                "actual": actual[name],
                "passed": actual[name] is not None
                and isclose(
                    actual[name],
                    expected,
                    rel_tol=catalog["relative_tolerance"],
                    abs_tol=catalog["absolute_tolerance"],
                ),
            }
            for name, expected in case["expected"].items()
        ]
        results.append(
            {
                "id": case["id"],
                "label": case["label"],
                "basis": case["basis"],
                "passed": all(m["passed"] for m in metrics),
                "metrics": metrics,
            }
        )
    return {
        "version": catalog["version"],
        "checked_at": datetime.now(UTC).isoformat(),
        "passed": all(r["passed"] for r in results),
        "passed_cases": sum(r["passed"] for r in results),
        "total_cases": len(results),
        "relative_tolerance": catalog["relative_tolerance"],
        "absolute_tolerance": catalog["absolute_tolerance"],
        "cases": results,
        "limitations": [
            "Internal hand-calculated reference checks; not independent plant/vendor validation or code certification.",
            "Cost correlations, regional factors, design margins and process completeness require project-specific review.",
            "BioSTEAM template mass/energy and transfer checks are run separately in the isolated trusted runner.",
        ],
    }


if __name__ == "__main__":
    result = reference_report()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
