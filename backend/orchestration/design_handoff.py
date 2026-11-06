"""Equipment specialist → chemical engineer → deterministic calculation handoff.

A bounded preliminary design proposal per failed equipment, never a fabricated
source observation. Existing priced selections and locked user inputs survive.
"""

from backend.equipment_costing.models import priced_record


import copy
import json

from backend.equipment_costing.registry import list_equipment_models

from .equipment_advisor import generate
from .pipeline import run

VERSION = "chemical-engineering-handoff-2"
INSTRUCTIONS = """You are FlowValue's chemical-engineering design specialist, receiving unresolved
items from the equipment specialist. Follow the founder's analyst workflow:
1. Read ALL supplied linked stream descriptions together, including later waste/output
mentions that identify a previously ambiguous tag. Process context is design intent,
not proof of numerical balance data. Streams without equipment remain boundaries or
unresolved, never invented assets. Challenge contradictory chemistry explicitly.
2. Select a physical cost configuration by service; keep alternative chart IDs editable.
Use the user's preferred chart when compatible, explain any incompatibility. Tank
shell proxies do not include complete ion exchange beds or packaging lines.
3. Propose preliminary explicit design assumptions to execute Python sizing: storage
hours, density, working fraction, EBCT/resin bed fraction, head DIFFERENCE, U/LMTD,
filtration loading, sensible Cp, kinetic residence time, gas properties as appropriate.
Do not return empty parameters solely because design data were not measured. These
are screening scenarios, not guaranteed performance or invented measurements.
Use bounded values and clear rationale/source. No outside research was performed.
For ion-exchange vessels use ion_exchange_ebct. The 15 min / 70% example is illustrative,
not compulsory data. For other vessels choose a justified retention/storage scenario.
4. Unit conversion/calculated capacity belongs to Python. Never calculate a mental
capacity then enter it as a direct size. Retain valid existing options/material factors.
If Python explicitly reports an out-of-range size and unsupported extrapolation,
choose a physically defensible preliminary scaling exponent and justification for
that equipment family, with limitations, or explain why even screening is unsafe.
The exponent is an editable engineering assumption, NOT a published textbook value.
Never clamp size, and never silently use a fitted graph slope as design validation.
5. AB means duty/standby ONLY if explicitly defined in this project's description.
When confirmed as duty+spare, charge two units of full duty capacity, not half each.
Do not also charge base-tag aliases as new units. Otherwise flag quantity uncertainty.
6. Every record gets either an executable preliminary proposal or a precise exception.
Do not invent a cost model for unsupported electrolyser packages or physically
incompatible service. No arbitrary probability/confidence numbers.
Use vaporizer_area for phase-change equipment rather than sensible-only exchanger_area.
For phase-change exchanger sizing, use explicit latent_heat_kj_kg, phase_change_fraction
and optional sensible_enthalpy_change_kj_kg with source/pressure/composition applicability.
For gas_compression use explicit gas inputs and constant-k single-stage applicability.
Never substitute sensible Cp for a vaporisation duty.
Never change approved manual prices or user-confirmed physical scope. Keep proxy
additions/exclusions in rationale. Do not silently certify safety/materials.
"""


def complete(
    report,
    description,
    plan,
    locked,
    store,
    provider,
    *,
    progress=None,
    repair_pass=False,
):
    if "equipment" in locked or provider is None:
        return copy.deepcopy(plan), [{"status": "skipped_locked_or_unavailable"}]
    current = copy.deepcopy(plan)
    baseline = run(report, description, current)
    lines = (baseline["stages"].get("equipment", {}).get("result") or {}).get(
        "equipment", []
    )
    failed = {
        r.get("parsed_source", {}).get("equipment_key")
        for r in lines
        if not priced_record(r)
        and r.get("decision", {}).get("scope_decision") != "alias"
        and not next(
            (
                p.get("manual_price", {}).get("locked", True)
                for p in current.get("equipment", [])
                if p.get("equipment_key")
                == r.get("parsed_source", {}).get("equipment_key")
                and p.get("manual_price")
            ),
            False,
        )
        and (not repair_pass or r.get("curve_id"))
    }
    equipment = [
        e for e in report["entities"] if e["kind"] == "equipment" and e["key"] in failed
    ]
    from backend.equipment_costing.registry import list_factors
    from backend.revenue.advisor import RevenueAIError

    catalogue = [
        {
            k: m[k]
            for k in (
                "id",
                "equipment",
                "configuration",
                "size_unit",
                "available_factor_ids",
                "observed_size_range",
                "input_requirements",
            )
            if k in m
        }
        for m in list_equipment_models()
    ]
    factors = {}
    for model in catalogue:
        for factor in list_factors(model["id"]):
            factors[factor["id"]] = factor
    policy = current.get("engineering_policy", {})
    audits = []
    for start in range(0, len(equipment), 3):
        group = equipment[start : start + 3]
        keys = {e["key"] for e in group}
        linked = {k for e in group for k in e.get("stream_keys", [])}
        entities = [e for e in report["entities"] if e["key"] in keys | linked]
        compact_entities = []
        for entity in entities:
            values, components = [], set()
            for value in entity.get("values", []):
                component = value.get("component")
                if component:
                    if (
                        value.get("normalized_value") in (None, 0, "0")
                        or component in components
                    ):
                        continue
                    components.add(component)
                values.append(
                    {
                        k: value.get(k)
                        for k in (
                            "id",
                            "property",
                            "component",
                            "normalized_value",
                            "normalized_unit",
                            "sheet",
                            "cell",
                            "status",
                        )
                    }
                )
            compact_entities.append(
                {
                    "key": entity["key"],
                    "identifier": entity["identifier"],
                    "kind": entity["kind"],
                    "stream_keys": entity.get("stream_keys", []),
                    "values": values,
                    "source_value_count": len(entity.get("values", [])),
                    "transport_note": "Zero/repeated composition bases omitted; full source observations retained in the register.",
                }
            )
        context = {
            "version": VERSION,
            "requested_sections": ["equipment", "capex"],
            "description": description,
            "equipment_batch": {"keys": sorted(keys)},
            "project_equipment_overview": [
                {"key": e["key"], "identifier": e["identifier"]}
                for e in report["entities"]
                if e["kind"] == "equipment"
            ],
            "report": {
                "entities": compact_entities,
                "connections": [
                    c
                    for c in report.get("connections", [])
                    if c.get("equipment_key") in keys
                ],
            },
            "available_models": catalogue,
            "available_factor_options": list(factors.values()),
            "preliminary_policy": policy,
            "previous_equipment": [
                p for p in current.get("equipment", []) if p["equipment_key"] in keys
            ],
            "python_feedback": [
                {
                    "tag": r["equipment_tag"],
                    "issues": r.get("issues", []),
                    "decision": r.get("decision", {}),
                    "sizing": r.get("parsed_source", {}).get("sizing"),
                }
                for r in lines
                if r.get("parsed_source", {}).get("equipment_key") in keys
            ],
        }
        if progress:
            progress("chemical_engineer_sizing:" + str(start // 3 + 1), "running")
        audit = {
            "equipment_keys": sorted(keys),
            "role": "chemical_engineer_design",
            "status": "unavailable",
        }
        for attempt in range(2):
            try:

                def checked(context=context, keys=keys):
                    from .planning_context import compact_transport

                    if len(json.dumps(compact_transport(context))) > 240000:
                        raise ValueError(
                            "Chemical-engineering region exceeds bounded source context; review source scope"
                        )
                    response = generate(provider, INSTRUCTIONS, context)
                    proposed = json.loads(
                        next(
                            section["value_json"]
                            for section in response["sections"]
                            if section["section"] == "equipment"
                        )
                    )
                    if (
                        len(proposed) != len(keys)
                        or {p["equipment_key"] for p in proposed} != keys
                    ):
                        raise ValueError(
                            "Design handoff must return exactly its assigned equipment"
                        )
                    return response

                response, cached = store.cached(context, checked)
                proposed = json.loads(
                    next(
                        section["value_json"]
                        for section in response["sections"]
                        if section["section"] == "equipment"
                    )
                )
                updates = {p["equipment_key"]: p for p in proposed}
                for item in updates.values():
                    options = item.setdefault("costing_options", {})
                    if policy.get("allow_provisional_graphs") is True:
                        options["allow_unverified"] = True
                    if policy.get("target_gallon_basis") in {"US", "Imperial"}:
                        options.setdefault("unit_context", {}).setdefault(
                            "target_gallon_basis", policy["target_gallon_basis"]
                        )
                    item["design_handoff"] = {
                        "role": "chemical_engineer_design",
                        "status": "assumed_preliminary",
                        "version": VERSION,
                        "external_research": False,
                    }
                current["equipment"] = [
                    updates.pop(p["equipment_key"], p)
                    for p in current.get("equipment", [])
                ] + list(updates.values())
                audit.update(
                    status="proposed_not_validated",
                    cached=cached,
                    attempts=attempt + 1,
                    questions=response.get("questions", []),
                )
                break
            except (
                ValueError,
                TypeError,
                KeyError,
                RuntimeError,
                TimeoutError,
                RevenueAIError,
            ) as exc:
                audit.update(attempts=attempt + 1, issue=str(exc)[:300])
        audits.append(audit)
        if progress:
            progress("chemical_engineer_sizing:" + str(start // 3 + 1), audit["status"])
    # Explicit project design basis, never a universal inference from tag spelling.
    standby = policy.get("duty_standby_suffixes", {})
    tags = {
        e["key"]: e["identifier"]
        for e in report["entities"]
        if e["kind"] == "equipment"
    }
    for item in current.get("equipment", []):
        if (item.get("manual_price") or {}).get("locked") is True:
            continue
        if item.get("scope_decision") == "alias":
            continue
        for suffix, basis in standby.items():
            if tags.get(item["equipment_key"], "").endswith(suffix):
                if (
                    basis.get("duty") != 1
                    or basis.get("standby") != 1
                    or not basis.get("source")
                ):
                    raise ValueError(
                        "Duty/standby policy requires explicit one-duty, one-spare source basis"
                    )
                item.update(
                    quantity=2,
                    quantity_rationale=basis["source"]
                    + "; one full-duty unit plus one full-duty spare, not a split duty",
                )
    if not repair_pass:
        current, repairs = complete(
            report,
            description,
            current,
            locked,
            store,
            provider,
            progress=progress,
            repair_pass=True,
        )
        audits.extend(repairs)
    from .approved_equipment import retain_approved

    current["equipment"] = retain_approved(
        plan.get("equipment", []), current.get("equipment", [])
    )
    return current, audits
