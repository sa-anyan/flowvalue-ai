"""Find alternative cost models without changing physical equipment sizing.

This is candidate discovery, not approval of configuration or cost scope. The
existing bounded AI review selects a suitable candidate and the canonical
registry performs scaling, factors and price translation. No universal exponent,
price, gallon basis, parallel train or complete-package scope is invented here.
"""

from .registry import list_equipment_models


def garrett_candidates(report, key, row, *, excluded=(), allow_graph=True, limit=8):
    """Recover omitted same-family Garrett options after a strict range failure.

    Only a valid saved Python sizing recipe can open this path. Dimensional
    compatibility alone is insufficient: family and recipe must also agree.
    Returned options still need service/material/pressure/scope review.
    """
    from backend.equipment_matching.library_preference import (
        FAMILY_TO_OPENPYTEA, user_selected_model,
    )
    from .unit_conversion.bridges.service import describe, evaluate, model_contract

    spec = row.get("unit_conversion") or {}
    match = row.get("matching") or {}
    if (row.get("manual_price") or row.get("external_quote")
            or row.get("scope_decision") in {"alias", "exclude"}
            or user_selected_model(row)
            or match.get("conceptual_validation") == "unsuitable"
            or match.get("model_scope") == "component_only"
            or not spec.get("enabled") or spec.get("model_id") != row.get("curve_id")):
        return []
    try:
        current, requirement, _ = model_contract(row["curve_id"])
        evaluate(report, key, spec)  # Missing/invalid sizing is not a range fallback.
    except (ValueError, KeyError, TypeError, OverflowError):
        return []
    source = current.get("source")
    if row["curve_id"] == "fermenter_reactor_turton_2001":
        families = {"Agitated tanks", "Reactors"}
        reactor_only = True
    elif source == "openpytea":
        category = str(current.get("category", "")).split(" / ")[0].strip()
        families = {family for family, categories in FAMILY_TO_OPENPYTEA.items()
                    if category in categories}
        reactor_only = category == "Reactors"
    else:
        # Other additional packages have different scope; a pH package must not
        # become a bare tank just because both accept a hydraulic coordinate.
        return []
    found = []
    for model in list_equipment_models("garrett"):
        if model["id"] in excluded or model.get("equipment") not in families:
            continue
        if reactor_only and "reactor" not in model.get("configuration", "").lower():
            continue
        interpretation = model.get("interpretation") or {}
        if interpretation.get("blocking_issues"):
            continue
        # Graph-use permission comes from the saved product/user policy.
        if not allow_graph:
            continue
        try:
            context = describe(report, key, model["id"])
            _, candidate_requirement, _ = model_contract(model["id"])
            if (context.get("issue")
                    or candidate_requirement.get("quantity") != requirement.get("quantity")
                    or spec.get("method") not in {r["id"] for r in context["recipes"]}):
                continue
        except (ValueError, KeyError, TypeError):
            continue
        found.append(model["id"])
    return found[:limit]
