"""Stage-specific planning data; full source evidence stays in the saved register.

Avoid resending component matrices and nested calculation audits to every planner.
Engineering interpretation already owns source checking; planners consume its
canonical totals, conditions and linked equipment, not a second raw Excel parse.
"""

import copy

DESIGN_PROPERTIES = {
    "name",
    "type",
    "description",
    "mass_flow",
    "molar_flow",
    "volume_flow",
    "temperature",
    "pressure",
    "density",
    "phase",
    "power",
    "heat_duty",
    "enthalpy_flow",
    "volume",
    "area",
    "length",
    "diameter",
    "height",
    "full_kw",
    "turn_kw",
    "turndown_kw",
    "source",
    "destination",
}
AUDITS = {
    "evidence",
    "provenance",
    "parsed_source",
    "operating_detail",
    "assumptions_json",
    "financial_inputs",
    "source_references",
    "cost_translation",
    "installation",
    "calculation",
}


def compact_context(context):
    result = copy.deepcopy(context)
    result["analyst_reviews"] = [
        {
            "role": r["role"],
            "status": r.get("status"),
            "summary": r.get("summary", "")[:600],
            "findings": [
                {
                    **{
                        k: f.get(k)
                        for k in (
                            "id",
                            "equipment_keys",
                            "topic",
                            "proposed_cost_owner",
                            "status",
                        )
                    },
                    "requirement": f.get("requirement", "")[:240],
                    "recommendation": f.get("recommendation", "")[:400],
                    "rationale": f.get("rationale", "")[:300],
                }
                for f in r.get("findings", [])
            ],
        }
        for r in result.get("analyst_reviews", [])
    ]
    if "equipment" not in result["requested_sections"]:
        for review in result["analyst_reviews"]:
            if review["role"] in {
                "process_equipment_engineer",
                "materials_hygiene_engineer",
                "health_safety_engineer",
            }:
                for finding in review["findings"]:
                    for field, limit in (
                        ("recommendation", 200),
                        ("rationale", 120),
                        ("requirement", 120),
                    ):
                        finding[field] = finding[field][:limit]
    result["specialist_context_note"] = (
        "Concise decision summaries; full independent findings and alternatives remain in the saved assessment."
    )
    for entity in result["report"]["entities"]:
        if "equipment" not in result["requested_sections"]:
            entity["component_observations"] = [
                {
                    k: v.get(k)
                    for k in ("id", "component", "property", "value", "unit", "source")
                }
                for v in entity["values"]
                if v.get("component") and v.get("value") not in (None, 0, "0", "0.0")
            ]
            observations = entity["component_observations"]
            by_component = {}
            rank = {
                "component_mass_flow": 0,
                "component_molar_flow": 1,
                "mass_fraction": 2,
                "mole_fraction": 3,
            }
            for observation in observations:
                name = observation.get("component")
                priority = rank.get(observation["property"], 9)
                if name not in by_component or priority < by_component[name][0]:
                    by_component[name] = (priority, [])
                if priority == by_component[name][0]:
                    by_component[name][1].append(observation)
            entity["component_observations"] = [
                row for _, rows in by_component.values() for row in rows
            ]
            entity["composition_basis_note"] = (
                "One available basis per component (mass preferred); original alternative bases retained in source register."
            )
            entity["zero_component_observations_omitted"] = True
        entity["values"] = [
            v for v in entity["values"] if v["property"] in DESIGN_PROPERTIES
        ]
    # Directed edges and mentions share endpoints; retain the process graph once.
    edges = {}
    for edge in result["report"]["connections"]:
        key = (edge.get("stream_key"), edge.get("equipment_key"), edge.get("role"))
        edges.setdefault(
            key,
            {
                k: edge[k]
                for k in ("stream_key", "equipment_key", "role", "status", "basis")
                if k in edge
            },
        )
    directional = {
        (edge.get("stream_key"), edge.get("equipment_key"))
        for edge in edges.values()
        if edge.get("role") != "mention"
    }
    result["report"]["connections"] = [
        edge
        for edge in edges.values()
        if edge.get("role") != "mention"
        or (edge.get("stream_key"), edge.get("equipment_key")) not in directional
    ]

    def summary(value):
        if isinstance(value, dict):
            return {k: summary(v) for k, v in value.items() if k not in AUDITS}
        if isinstance(value, list):
            return [summary(v) for v in value]
        return value

    if "equipment" not in result["requested_sections"]:
        result["plan"] = {
            k: v
            for k, v in result.get("plan", {}).items()
            if k != "equipment"
            and (k != "capex" or "capex" in result["requested_sections"])
        }
        if "capex" not in result["requested_sections"]:
            result["capex_factors"] = []
    if "equipment" not in result["requested_sections"]:
        capital = result.get("calculated_stage_summary", {}).get("capex", {})
        if capital.get("result"):
            capital["result"] = {
                k: v
                for k, v in capital["result"].items()
                if k
                in {
                    "model_id",
                    "process_type",
                    "status",
                    "currency",
                    "period",
                    "purchased_equipment",
                    "direct_costs",
                    "indirect_costs",
                    "plant_cost",
                    "fixed_capital",
                    "startup_expenses",
                    "working_capital",
                    "total_capex",
                    "issues",
                }
            }
    stage_summary = result.get("calculated_stage_summary", {})
    if "equipment" not in result["requested_sections"]:
        engineering = stage_summary.get("engineering_data", {})
        if isinstance(engineering.get("result"), dict):
            original = engineering["result"]
            engineering["result"] = {
                k: original.get(k)
                for k in (
                    "status",
                    "filename",
                    "equipment_count",
                    "material_stream_count",
                    "energy_stream_count",
                )
            }
            engineering["result"]["issue_count"] = len(original.get("issues", []))
        equipment = stage_summary.get("equipment", {})
        if isinstance(equipment.get("result"), dict):
            original = equipment["result"]
            equipment["result"] = {
                k: v
                for k, v in original.items()
                if k
                in {
                    "status",
                    "complete",
                    "currency",
                    "period",
                    "total_equipment_cost",
                    "total_installation_cost",
                    "total_equipment_and_installation_cost",
                    "subtotal",
                    "unpriced",
                    "priced_count",
                    "unpriced_count",
                }
            }
            equipment["result"]["equipment"] = []
            for row in original.get("equipment", []):
                item = {
                    k: row.get(k)
                    for k in (
                        "equipment_tag",
                        "curve_id",
                        "equipment_cost",
                        "installation_cost",
                        "equipment_and_installation_cost",
                        "amount",
                        "cost_scope",
                        "quantity",
                        "status",
                        "pricing_status",
                    )
                }
                estimate = row.get("calculation") or {}
                estimate = estimate.get("estimate") or {}
                item["price_basis"] = {
                    k: estimate.get(k)
                    for k in ("currency", "period", "index_series", "index_value")
                }
                equipment["result"]["equipment"].append(item)
            equipment["audit_note"] = (
                "Sizing/matching/audit trees retained in source assessment; economic planner receives costs and bases only."
            )
    result["calculated_stage_summary"] = summary(stage_summary)
    # Revenue source_streams is another complete copy of totals. The operating
    # planner needs it; equipment planning already has the same linked streams.
    result["parsed_revenue_streams"] = []
    result["revenue_stream_note"] = (
        "Use the same canonical material records and normalized totals in report.entities; a redundant copy of these streams was omitted."
    )
    result["planning_basis"] = (
        "Compact reviewed totals/conditions; original component observations, units, cells and audit trails remain in the assessment. Missing physical properties are not zero."
    )
    return result


def equipment_batches(context, batch_size=6):
    equipment = [e for e in context["report"]["entities"] if e["kind"] == "equipment"]
    errors = context.get("calculated_stage_summary", {}).get("engineering_errors", [])
    if errors:
        failed_tags = {e["equipment_tag"] for e in errors}
        equipment = [e for e in equipment if e["identifier"] in failed_tags]
    overview = [
        {
            "key": e["key"],
            "tag": e["identifier"],
            "service": [
                v.get("value")
                for v in e["values"]
                if v["property"] in {"name", "type", "description"}
            ],
        }
        for e in context["report"]["entities"]
        if e["kind"] == "equipment"
    ]
    for start in range(0, len(equipment), batch_size):
        batch = copy.deepcopy(context)
        selected = equipment[start : start + batch_size]
        keys = {e["key"] for e in selected}
        streams = {s for e in selected for s in e.get("stream_keys", [])}
        batch["report"]["entities"] = [
            e
            for e in context["report"]["entities"]
            if e["key"] in keys or e["key"] in streams
        ]
        batch["report"]["connections"] = [
            c
            for c in context["report"]["connections"]
            if c.get("equipment_key") in keys
        ]
        batch["analyst_reviews"] = [
            {
                **review,
                "findings": [
                    f
                    for f in review.get("findings", [])
                    if not f.get("equipment_keys")
                    or keys.intersection(f["equipment_keys"])
                ],
            }
            for review in context.get("analyst_reviews", [])
        ]
        batch["project_equipment_overview"] = context.get(
            "project_equipment_overview", overview
        )
        batch.setdefault("plan", {})["equipment"] = (
            [
                r
                for r in context.get("plan", {}).get("equipment", [])
                if r["equipment_key"] in keys
            ]
            if "plan" in batch
            else []
        )
        batch["equipment_batch"] = {
            "index": start // batch_size + 1,
            "total_equipment": len(equipment),
            "keys": sorted(keys),
        }
        import json

        if (
            len(json.dumps(compact_transport(batch), default=str)) > 220000
            and len(selected) > 1
        ):
            yield from equipment_batches(batch, max(1, len(selected) // 2))
        else:
            yield batch


def compact_transport(context):
    """Columnar catalogues preserve every value/ID while avoiding repeated field names."""
    result = copy.deepcopy(context)
    for key in ("available_models", "available_factor_options"):
        records = result.get(key, [])
        if records and isinstance(records[0], dict):
            columns = list(dict.fromkeys(k for record in records for k in record))
            result[key + "_columns"] = columns
            result[key] = [[record.get(k) for k in columns] for record in records]
    if isinstance(result.get("report"), dict):
        for field, header in (
            ("values", "value_columns"),
            ("component_observations", "component_observation_columns"),
        ):
            columns = list(
                dict.fromkeys(
                    k
                    for entity in result["report"]["entities"]
                    for record in entity.get(field, [])
                    if isinstance(record, dict)
                    for k in record
                )
            )
            if columns:
                result["report"][header] = columns
                for entity in result["report"]["entities"]:
                    entity[field] = [
                        [r.get(k) for k in columns] for r in entity.get(field, [])
                    ]
    if isinstance(result.get("report"), dict):
        records = result["report"].get("connections", [])
        if records and isinstance(records[0], dict):
            columns = list(dict.fromkeys(k for r in records for k in r))
            result["report"]["connection_columns"] = columns
            result["report"]["connections"] = [
                [r.get(k) for k in columns] for r in records
            ]
    for review in result.get("analyst_reviews", []):
        findings = review.get("findings", [])
        if findings and isinstance(findings[0], dict):
            columns = list(dict.fromkeys(k for f in findings for k in f))
            review["finding_columns"] = columns
            review["findings"] = [[f.get(k) for k in columns] for f in findings]
    return result
