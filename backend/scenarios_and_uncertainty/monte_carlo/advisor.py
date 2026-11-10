"""One-time, bounded range proposals through the existing engineering provider.

No research calls, fabricated measurements or per-iteration LLM execution.
"""

import copy
import json

from backend.orchestration.equipment_advisor import validate as validate_shape
from backend.revenue.advisor import TEXT, obj

from .discovery import discover
from .models import Settings
from .sampling import validate


def recommend(state, store, provider):
    discovery = discover(state)
    original = Settings.model_validate(discovery["settings"])
    report = (
        state.get("scoped_report")
        or state.get("effective_report")
        or state["parsed"]["report"]
    )
    needed = [
        p
        for p in original.parameters
        if p.kind in {"engineering", "economic"}
        and not p.review_required
        and (p.minimum is None or p.maximum is None or p.mode is None)
        and p.targets[0][0] not in state.get("locked", [])
    ]
    proposals = []
    audit = []
    for start in range(0, len(needed), 4):
        group = needed[start : start + 4]
        ids = [p.id for p in group]
        # Source conditions and design facts, not another complete component workbook dump.
        context = {
            "role": "chemical_engineer_uncertainty",
            "description": state["description"],
            "parameters": [p.model_dump() for p in group],
            "equipment_context": [
                {
                    "key": e["key"],
                    "identifier": e["identifier"],
                    "kind": e["kind"],
                    "stream_keys": e.get("stream_keys", []),
                    "values": [
                        {
                            k: v.get(k)
                            for k in (
                                "id",
                                "property",
                                "normalized_value",
                                "normalized_unit",
                                "sheet",
                                "cell",
                            )
                        }
                        for v in e["values"]
                        if not v.get("component")
                    ],
                }
                for e in report["entities"]
            ],
            "operating_assumptions": state["plan"].get("operating_economics", {}),
            "capital_assumptions": state["plan"].get("capex", {}),
            "source_notice": "Existing workbook/assumptions only. No market or literature research was performed.",
        }
        schema = obj(
            {
                "proposals": {
                    "type": "array",
                    "items": obj(
                        {
                            "id": {"type": "string", "enum": ids},
                            "status": {
                                "type": "string",
                                "enum": ["proposed", "unresolved"],
                            },
                            "minimum": {"type": ["number", "null"]},
                            "mode": {"type": ["number", "null"]},
                            "maximum": {"type": ["number", "null"]},
                            "stddev": {"type": ["number", "null"]},
                            "distribution": {
                                "type": "string",
                                "enum": [
                                    "triangular",
                                    "uniform",
                                    "normal",
                                    "lognormal",
                                ],
                            },
                            "source": TEXT,
                            "rationale": TEXT,
                            "confidence": TEXT,
                        }
                    ),
                }
            }
        )
        instructions = """Act as the existing Chemical Engineer and Techno-economic Analyst Specialist. Review uncertainty in equipment sizing and costing inputs, capital factors, operating costs, and commercial assumptions. Propose bounds around existing economic estimates only when their basis supports it; do not invent new revenue methods, market quotes or equation coefficients. Published allowable factor intervals are not measured probability distributions. Propose editable preliminary ranges only when physically defensible from this process and the supplied source context. Select an appropriate bounded distribution and explain it. For a known baseline central value, retain it; never overwrite a workbook or user value. A missing duty may be an explicitly labelled engineering scenario, never a measured value. Return unresolved if no defensible range exists. No external research was performed: do not invent citations or claim published data not supplied. Confidence must be qualitative with its basis; no calibrated probability or numeric confidence score is available. Python performs calculations. Triangular uses mode; normal uses mean and absolute standard deviation; lognormal uses median and log-space sigma. Respect given physical/method limits."""

        def call(
            context=context,
            schema=schema,
            instructions=instructions,
            group=group,
            ids=ids,
        ):
            if len(json.dumps(context)) > 240000:
                raise ValueError(
                    "Engineering range context exceeds bounded input limit"
                )
            value = provider.generate(
                instructions=instructions, context=context, schema=schema
            )
            validate_shape(value, schema)
            if len(value["proposals"]) != len(group) or {
                p["id"] for p in value["proposals"]
            } != set(ids):
                raise ValueError(
                    "Range specialist must address every assigned parameter once"
                )
            return value

        try:
            value, cached = store.cached(context, call)
            for proposal in value["proposals"]:
                p = next(p for p in group if p.id == proposal["id"])
                if proposal["status"] == "unresolved":
                    audit.append(proposal)
                    continue
                patch = {
                    k: proposal[k]
                    for k in (
                        "minimum",
                        "mode",
                        "maximum",
                        "stddev",
                        "distribution",
                        "source",
                        "rationale",
                        "confidence",
                    )
                }
                if p.mode is not None and patch["mode"] != p.mode:
                    raise ValueError(
                        "Range proposal cannot overwrite an existing central value"
                    )
                patch["source"] = (
                    "Unverified AI engineering proposal from supplied project context: "
                    + patch["source"]
                )
                patch["confidence"] = (
                    "Uncalibrated engineering judgement; see rationale. No numerical confidence basis."
                )
                candidate = type(p).model_validate(
                    {**p.model_dump(), **patch, "enabled": True}
                )
                validate(Settings(parameters=[candidate]), original)
                proposals.append(
                    {
                        **candidate.model_dump(),
                        "enabled": False,
                        "review_status": "AI draft; user must enable after review",
                    }
                )
            audit.append({"parameters": ids, "status": "draft", "cached": cached})
        except (ValueError, TypeError, KeyError, RuntimeError) as exc:
            audit.append(
                {"parameters": ids, "status": "unavailable", "reason": str(exc)[:400]}
            )
    return copy.deepcopy(proposals), audit
