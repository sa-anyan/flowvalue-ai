"""Apply the founder's human-study prices to a separate local Charlie version.

Run from repository root: python -m scripts.apply_charlie_pricing --assessment ID --workbook FILE
No parser changes, provider calls, external research, simulation or deployment.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from openpyxl import load_workbook

from backend.equipment_costing.cost_to_future.cost_translation import DEFAULT_POLICY
from backend.equipment_costing.indexes.garrett.installation import installation_policy
from backend.equipment_costing.total_cost.calculator import calculate_total_cost
from backend.orchestration.pipeline import run
from backend.orchestration.store import Store


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--assessment", required=True)
    cli.add_argument("--workbook", type=Path, required=True)
    cli.add_argument("--database", default="outputs/assessments/local.sqlite3")
    args = cli.parse_args()
    profile = json.loads(
        Path("backend/equipment_costing/charlie_project_benchmarks.json").read_text()
    )
    content = args.workbook.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    book = load_workbook(args.workbook, data_only=True, read_only=True)
    store = Store(args.database)
    baseline = store.get(args.assessment)
    state = copy.deepcopy(baseline)
    report = copy.deepcopy(
        state.get("scoped_report")
        or state.get("effective_report")
        or state["parsed"]["report"]
    )
    entities = {
        e["identifier"]: e for e in report["entities"] if e["kind"] == "equipment"
    }
    plan = state["plan"]
    previous = {p["equipment_key"]: copy.deepcopy(p) for p in plan["equipment"]}
    proposals = {
        e["identifier"]: next(
            p for p in plan["equipment"] if p["equipment_key"] == e["key"]
        )
        for e in entities.values()
    }
    plan["cost_translation"] = {**DEFAULT_POLICY, **plan.get("cost_translation", {})}
    before = run(report, state["description"], copy.deepcopy(plan))
    for tag, decision in profile["benchmarks"].items():
        row = proposals[tag]
        source_sheet = decision.get("sheet", profile["source_sheet"])
        cell = decision["cell"]
        raw = book[source_sheet][cell] if ":" not in cell else None
        source = {
            "workbook": args.workbook.name,
            "sha256": digest,
            "sheet": source_sheet,
            "cell": cell,
            "cached_value": raw.value if raw else None,
            "selected_amount": decision["amount"],
            "currency": "USD",
            "basis_note": profile["basis_note"],
        }
        quantity = decision.get("quantity", row.get("quantity", 1))
        unit_price = (
            decision["amount"] / quantity
            if decision.get("record_total")
            else decision["amount"]
        )
        notes = (
            "Human-developed engineering estimate accepted by founder for the demonstration; not a current vendor quotation. "
            + decision.get("note", "")
        )
        if decision.get("record_total"):
            notes += " Workbook AB-row amount is provisionally the pair/package total; divide by installed quantity once, retaining the original aggregate price."
        if decision.get("proxy_of"):
            notes += (
                " Separate asset proxy from "
                + decision["proxy_of"]
                + " at assumed comparable capacity; possible identity/duplication retained for review."
            )
        manual = {
            "amount": unit_price,
            "currency": "USD",
            "price_period": profile["price_period_assumption"],
            "source": f"{args.workbook.name} | {source_sheet}!{cell} | SHA256 {digest}",
            "notes": notes,
            "cost_scope": "purchased_equipment",
            "approved": True,
            "locked": True,
            "configuration": decision["type"],
            "cost_status": "provisional_proxy"
            if decision.get("proxy_of")
            else "project_benchmark",
            "source_record": source,
        }
        if decision.get("factor_model"):
            policy = installation_policy(decision["factor_model"])
            factor = policy.get("default") or {}
            if factor.get("multiplier"):
                manual.update(
                    installation_factor=factor["multiplier"],
                    installation_rationale="Existing Garrett equipment-family factor, provisional applicability; not a second whole-plant CAPEX installation charge.",
                    installation_source={
                        "curve_id": decision["factor_model"],
                        **factor,
                    },
                )
        row.update(
            manual_price=manual,
            quantity=quantity,
            scope_decision="include",
            alias_of=None,
            alias_confirmation=None,
            rationale=notes,
            human_study_previous_plan=previous[row["equipment_key"]],
        )
        evidence = {
            "id": "human-study:" + tag,
            "property": "type",
            "normalized_value": decision["type"],
            "normalized_unit": None,
            "original_value": decision["type"],
            "original_unit": None,
            "workbook": args.workbook.name,
            "sheet": source_sheet,
            "cell": cell.replace("C", "B") if ":" not in cell else cell,
            "status": "inferred",
            "note": "Founder-selected human study interpretation; competing M&E interpretation retained in original values.",
        }
        entities[tag]["values"].append(evidence)
    for tag, target in profile["aliases"].items():
        row = proposals[tag]
        row.update(
            scope_decision="alias",
            alias_of=entities[target]["key"],
            manual_price=None,
            alias_confirmation={
                "status": "user_confirmed",
                "rationale": "Founder explicitly selected probable alias as provisional demonstration basis; distinct-asset alternative retained in source history.",
            },
            rationale="Provisional alias of "
            + target
            + "; reference its price and add no duplicate cost.",
            human_study_previous_plan=previous[row["equipment_key"]],
        )
    state["scoped_report"] = report
    state["human_study_pricing"] = {
        "profile": profile,
        "source_workbook": args.workbook.name,
        "sha256": digest,
        "baseline": baseline["id"],
        "status": "founder_selected_provisional_demonstration",
        "alternatives_retained": True,
    }
    state["locked"] = sorted(set(state.get("locked", [])) | {"equipment"})
    after = run(report, state["description"], plan)
    state["results"] = after
    state["running"] = False
    state["status"] = "Charlie — human-study pricing demonstration; provisional basis"
    # One focused pricing/alias check, and one canonical CAPEX integration smoke check.
    lines = after["stages"]["equipment"]["result"]["equipment"]
    by_tag = {r["equipment_tag"]: r for r in lines}
    target_tags = [
        "T-104",
        "T-101",
        "R-101",
        "T-105",
        "S-201",
        "FT-201",
        "PD-201AB",
        "PD-201",
        "C-201",
        "R-201",
    ]
    for tag in target_tags:
        row = by_tag[tag]
        assert row.get("equipment_cost") is not None or (
            row.get("reference_cost", {}).get("purchase_cost") is not None
            and row["additional_purchase_cost"] == 0
        ), tag
    assert sum(r.get("cost_status") == "alias_reference" for r in lines) == 3
    purchase = sum(
        r["equipment_cost"] for r in lines if r["equipment_cost"] is not None
    )
    capex = after["stages"]["capex"]["result"]
    assert capex and capex["total_capex"] is not None, after["stages"]["capex"]
    assert abs(float(capex["purchased_equipment"]) - purchase) < 0.01
    trial = calculate_total_cost(
        [
            {
                "equipment_tag": "override smoke",
                "manual_price": {**proposals["R-101"]["manual_price"], "amount": 12345},
                "quantity": 1,
            }
        ],
        translation_policy={"enabled": False},
    )
    assert trial.equipment_cost_total == 12345
    saved = store.create(
        {**state, "parent_assessment": baseline["id"]}, store.workbook(baseline["id"])
    )
    assert store.get(baseline["id"]) == baseline
    root = Path("outputs/charlie-immediate-pricing")
    root.mkdir(parents=True, exist_ok=True)
    report_out = {
        "assessment": saved["id"],
        "baseline": baseline["id"],
        "checks": "10/10 cost or priced reference; three aliases add no charge; canonical purchased subtotal reconciles to CAPEX; manual override passed",
        "price_period": capex["period"],
        "currency": capex["currency"],
        "purchase_total": purchase,
        "capex_before": before["stages"]["capex"]["result"]["total_capex"],
        "capex_after": capex["total_capex"],
        "capex_change": float(capex["total_capex"])
        - float(before["stages"]["capex"]["result"]["total_capex"]),
        "records": [
            {
                k: r.get(k)
                for k in [
                    "equipment_tag",
                    "equipment_cost",
                    "installation_cost",
                    "equipment_and_installation_cost",
                    "cost_status",
                    "reference_cost",
                    "additional_purchase_cost",
                ]
            }
            for r in lines
            if r["equipment_tag"] in target_tags
        ],
        "assumptions": profile,
    }
    (root / "result.json").write_text(json.dumps(report_out, indent=2))
    print(json.dumps(report_out, indent=2))
    book.close()


if __name__ == "__main__":
    main()
