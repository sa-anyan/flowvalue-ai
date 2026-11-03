"""Bounded repair of invalid AI register references; never changes numerical inputs."""

import copy


def repair(value, report, provider):
    result = copy.deepcopy(value)
    entities = report.get("entities", [])
    if not entities:
        return result
    by_kind = {
        kind: {e["key"]: e for e in entities if e["kind"] == kind}
        for kind in ("material", "equipment")
    }
    for group in ("sales", "materials", "energy"):
        for item in result.get(group, []):
            for field, kind in (
                ("stream_key", "material"),
                ("source_key", "material"),
                ("equipment_key", "equipment"),
            ):
                key = item.get(field)
                if key is None or key in by_kind[kind]:
                    continue
                options = by_kind[kind]
                schema = {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["key", "rationale"],
                    "properties": {
                        "key": {"type": ["string", "null"], "enum": [None, *options]},
                        "rationale": {"type": "string"},
                    },
                }
                response = provider.generate(
                    instructions="Repair only this invalid register reference. Select an actual supplied key only if its source identity supports the intended item; otherwise return null. Do not invent a connection or change numerical assumptions.",
                    context={
                        "item": item,
                        "field": field,
                        "choices": [
                            {
                                "key": e["key"],
                                "identifier": e.get("identifier"),
                                "description": e.get("name"),
                                "source": e.get("id_evidence"),
                                "labels": [
                                    v.get("original_value")
                                    for v in e.get("values", [])
                                    if v.get("property") in {"name", "description"}
                                ],
                            }
                            for e in options.values()
                        ],
                    },
                    schema=schema,
                )
                corrected = response.get("key")
                if corrected not in options:
                    raise ValueError(
                        "Unresolved engineering register reference: " + str(key)
                    )
                item[field] = corrected
                result.setdefault("reference_repairs", []).append(
                    {
                        "group": group,
                        "id": item.get("id"),
                        "field": field,
                        "original": key,
                        "selected": corrected,
                        "rationale": response.get("rationale"),
                        "status": "inferred_review_required",
                    }
                )
    return result


def repair_energy(value, report, provider):
    """Request explicit missing energy assumptions; do not infer heat from enthalpy alone."""
    result = copy.deepcopy(value)
    entities = {e["key"]: e for e in report.get("entities", [])}
    for item in result.get("energy", []):
        if (
            item.get("method")
            not in {"thermal_duty", "shaft_power", "electrical_assumption"}
            or item.get("power_kw") is not None
        ):
            continue
        response = provider.generate(
            instructions="This preliminary energy scenario is missing power_kw. Review supplied evidence. Propose an explicit preliminary duty assumption only if physically defensible, with rationale and uncertainty; source enthalpy flow is not automatically heat duty. Otherwise return null. This is not measured or verified consumption. Do not change equipment or stream identity.",
            context={"item": item, "source": entities.get(item.get("source_key"))},
            schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["power_kw", "rationale", "uncertainty"],
                "properties": {
                    "power_kw": {"type": ["number", "null"], "minimum": 0},
                    "rationale": {"type": "string"},
                    "uncertainty": {"type": "string"},
                },
            },
        )
        power = response.get("power_kw")
        if (
            power is None
            or isinstance(power, bool)
            or not isinstance(power, (int, float))
            or power < 0
        ):
            raise ValueError("Unresolved energy demand: " + item.get("id", ""))
        item.update(
            power_kw=power,
            rationale=response["rationale"],
            uncertainty=response["uncertainty"],
        )
        result.setdefault("energy_assumption_repairs", []).append(
            {
                "id": item.get("id"),
                "power_kw": power,
                "status": "llm_estimate",
                "rationale": response["rationale"],
                "uncertainty": response["uncertainty"],
            }
        )
    return result
