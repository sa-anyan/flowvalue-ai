"""Canonical equipment handoff; no other stage is executed here."""

import copy
from decimal import Decimal, InvalidOperation
from backend.equipment_costing.total_cost.calculator import calculate_total_cost
from backend.equipment_costing.unit_conversion import ConversionContext
from backend.orchestration.codec import construct, plain
from backend.orchestration.sizing import derive_size
from backend.equipment_resolution.scope import confirmed


def calculate_equipment(report, plan, translation_policy=None):
    objects = {}
    parsed = {e["key"]: e for e in report["entities"] if e["kind"] == "equipment"}
    chosen = {}
    for row in plan.get("equipment", []):
        key = row.get("equipment_key")
        if key not in parsed:
            reference = str(
                key or row.get("equipment_tag") or row.get("identifier") or ""
            )
            token = "".join(c for c in reference.casefold() if c.isalnum())
            matches = [
                k
                for k, e in parsed.items()
                if token
                and token
                == "".join(c for c in e["identifier"].casefold() if c.isalnum())
            ]
            if len(matches) == 1:
                key = matches[0]
        if key in parsed and key not in chosen:
            chosen[key] = row
    rows = []
    for key, entity in parsed.items():
        proposal = chosen.get(key, {})
        options = copy.deepcopy(proposal.get("costing_options") or {})
        if proposal.get("scope_decision") == "alias":
            target = proposal.get("alias_of")
            if target not in parsed or target == key:
                target = "unresolved alias target"
            proposal = {
                **proposal,
                "curve_id": None,
                "external_quote": None,
                "manual_price": None,
                "size": None,
                "sizing": None,
                "rationale": "Proposed alias of "
                + target
                + "; not priced twice. "
                + proposal.get("rationale", ""),
            }
        sizing_evidence = None
        sizing_issue = None
        try:
            if not isinstance(options, dict):
                raise ValueError("Equipment costing options must be an object")
            if isinstance(options.get("unit_context"), dict):
                options["unit_context"] = construct(
                    ConversionContext, options["unit_context"]
                )
            conversion = proposal.get("unit_conversion") or {}
            if (
                conversion.get("enabled")
                and not proposal.get("manual_price")
                and not proposal.get("external_quote")
                and proposal.get("scope_decision") != "alias"
            ):
                from backend.equipment_costing.unit_conversion.bridges.service import (
                    evaluate,
                )

                if conversion.get("model_id") != proposal.get("curve_id"):
                    raise ValueError(
                        "Unit conversion model changed; review its assumptions"
                    )
                sizing_evidence = evaluate(report, key, conversion)
                size, size_unit = sizing_evidence["size"], sizing_evidence["size_unit"]
            else:
                size, size_unit, sizing_evidence = derive_size(proposal, report)
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            options = options if isinstance(options, dict) else {}
            options.pop("unit_context", None)
            size, size_unit = None, proposal.get("size_unit")
            sizing_issue = str(exc)
        if isinstance(size, str):
            try:
                size = float(Decimal(size))
            except (InvalidOperation, ValueError, OverflowError):
                pass  # Canonical unit validator retains the unsupported value as an issue.
        rows.append(
            {
                "equipment_tag": entity["identifier"] or key,
                "source": (
                    "nottingham"
                    if str(proposal.get("curve_id", "")).startswith("N501-")
                    else (proposal.get("source") or "garrett")
                ),
                "curve_id": (
                    "manual:user-price"
                    if proposal.get("manual_price")
                    else (
                        "external:reviewed-comparable"
                        if proposal.get("external_quote")
                        else proposal.get("curve_id")
                    )
                ),
                "external_quote": proposal.get("external_quote"),
                "manual_price": proposal.get("manual_price"),
                "separate_scope_conflicts": True,
                "size": size,
                "size_unit": size_unit,
                "quantity": proposal.get("quantity", 1),
                "costing_options": options,
                "parsed_source": {
                    "equipment_key": key,
                    "conceptual_matching": proposal.get("matching"),
                    "confirmed_alias": proposal.get("scope_decision") == "alias"
                    and confirmed(proposal),
                    "parent_equipment_key": entity.get("parent_equipment_key"),
                    "name": next(
                        (
                            v.get("normalized_value")
                            for v in reversed(entity["values"])
                            if v["property"] == "name"
                        ),
                        entity["identifier"],
                    ),
                    "classification": next(
                        (
                            v.get("normalized_value")
                            for v in reversed(entity["values"])
                            if v["property"] == "type"
                        ),
                        "",
                    ),
                    "stream_keys": entity.get("stream_keys", []),
                    "evidence": entity["values"],
                    "sizing": sizing_evidence,
                    "sizing_issue": sizing_issue,
                    "rationale": proposal.get(
                        "rationale", "No supported model/sizing supplied"
                    ),
                },
            }
        )
    objects["equipment_sizing_rows"] = rows
    return calculate_total_cost(rows, translation_policy=translation_policy), rows
