"""Discover stored engineering ranges; never manufacture missing source measurements."""

import math

from backend.equipment_costing.models import priced_record


from backend.engineering_sizing.registry import PARAMETER_UNITS

from .models import Parameter, Settings


def numeric(value):
    try:
        number = float(value)
        return number if not isinstance(value, bool) and math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def get(plan, path):
    value = plan
    for key in path:
        value = value[key]
    return value


def set_value(plan, path, value):
    target = plan
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


def discover(state):
    plan = state["plan"]
    report = (
        state.get("scoped_report")
        or state.get("effective_report")
        or state["parsed"]["report"]
    )
    from backend.equipment_resolution.scope import expand

    report, _ = expand(report, plan)
    entities = {e["key"]: e for e in report["entities"] if e["kind"] == "equipment"}
    params = []

    def add(path, label, unit, value, low=None, high=None, *, auto_enable=True, **kw):
        mode, low, high = map(numeric, (value, low, high))
        hard_min, hard_max = kw.get("hard_min"), kw.get("hard_max")
        ready = (
            mode is not None and low is not None and high is not None
            and low < high and low <= mode <= high
            and (hard_min is None or (low > hard_min if kw.get("strictly_positive") else low >= hard_min))
            and (hard_max is None or high <= hard_max)
        )
        if ready:
            kw.setdefault("rationale", "Triangular scenario using the saved value as its most likely point.")
            if not kw["rationale"].strip():
                kw["rationale"] = "Triangular scenario using the saved value as its most likely point."
        item = Parameter(
                id=".".join(map(str, path)),
                label=label,
                targets=[path],
                unit=unit,
                mode=mode,
                minimum=low,
                maximum=high,
                enabled=ready and auto_enable,
                **kw,
        )
        params.append(item)
        return item

    from backend.equipment_resolution.scope import equipment_paths

    for prefix, row in equipment_paths(plan):
        tag = entities.get(row.get("equipment_key"), {}).get(
            "identifier", row.get("equipment_key", "Equipment")
        )
        conversion = row.get("unit_conversion") or {}
        if conversion.get("enabled") and not (row.get("manual_price") or row.get("external_quote")):
            from backend.equipment_costing.unit_conversion.bridges.service import PARAMETERS

            for key, value in (conversion.get("inputs") or {}).items():
                if key not in PARAMETERS or numeric(value) is None:
                    continue
                evidence = (conversion.get("input_provenance") or {}).get(key) or {}
                if not isinstance(evidence, dict):
                    evidence = {}
                add(
                    [*prefix, "unit_conversion", "inputs", key],
                    f"{tag} · {key.replace('_', ' ')}", PARAMETERS[key], value,
                    evidence.get("low"), evidence.get("high"),
                    source=str(evidence.get("source") or "Saved equipment conversion input"),
                    rationale=str(evidence.get("rationale") or conversion.get("rationale") or ""),
                )
        for key, p in (row.get("sizing") or {}).get("parameters", {}).items():
            if conversion.get("enabled") and not (row.get("manual_price") or row.get("external_quote")):
                continue  # The active conversion owns the size used by the calculator.
            if not isinstance(p, dict):
                continue
            fraction = key in {
                "efficiency",
                "working_fraction",
                "resin_bed_fraction",
                "lmtd_correction",
                "phase_change_fraction",
                "feed_water_mass_fraction",
                "product_water_mass_fraction",
            }
            add(
                [*prefix, "sizing", "parameters", key, "value"],
                f"{tag} · {key.replace('_', ' ')}",
                p.get("unit") or PARAMETER_UNITS.get(key, ("",))[0],
                p.get("value"),
                p.get("low"),
                p.get("high"),
                source=str(p.get("source") or "Saved engineering assumption"),
                rationale=str(p.get("rationale") or ""),
                hard_min=1 if key == "heat_capacity_ratio" else 0,
                hard_max=1 if fraction else 2 if key == "heat_capacity_ratio" else None,
                strictly_positive=key
                not in {
                    "product_water_mass_fraction",
                    "sensible_enthalpy_change_kj_kg",
                },
            )
        if not row.get("sizing") and row.get("size") is not None:
            add(
                [*prefix, "size"],
                f"{tag} · supplied size",
                row.get("size_unit", ""),
                row["size"],
                source="Saved explicit equipment size; range requires review",
                hard_min=0,
                strictly_positive=True,
            )
        manual = row.get("manual_price") or {}
        if manual.get("amount") is not None:
            add(
                [*prefix, "manual_price", "amount"],
                f"{tag} · user price",
                str(manual.get("currency", "")) + "/equipment",
                manual["amount"],
                manual.get("amount_low"), manual.get("amount_high"),
                source=str(manual.get("source", "User price")),
                rationale=str(manual.get("notes", "")),
                kind="economic",
                hard_min=0,
                strictly_positive=True,
            )
        quote = row.get("external_quote") or {}
        if quote.get("amount") is not None:
            add(
                [*prefix, "external_quote", "amount"],
                f"{tag} · benchmark reference price",
                str(quote.get("currency", "")) + "/equipment",
                quote["amount"],
                quote.get("amount_low"), quote.get("amount_high"),
                source=str(quote.get("source_url", "Saved reviewed comparable")),
                rationale=str(
                    quote.get(
                        "rationale",
                        "Range around the reviewed benchmark requires explicit justification",
                    )
                ),
                kind="economic",
                hard_min=0,
                strictly_positive=True,
            )
        candidates = list(
            dict.fromkeys([row.get("curve_id"), *row.get("candidate_curve_ids", [])])
        )
        candidates = [c for c in candidates if c and not c.startswith("external:")]
        if candidates:
            params.append(
                Parameter(
                    id=".".join(map(str, [*prefix, "curve_id"])),
                    label=f"{tag} · alternative cost configuration",
                    targets=[[*prefix, "curve_id"]],
                    unit="model_id",
                    distribution="discrete",
                    choices=candidates,
                    probabilities=[1 / len(candidates)] * len(candidates),
                    kind="configuration",
                    source="Existing selected/candidate catalogue configurations",
                    rationale="Compatibility, scope and probability weights require review; alternatives are not assumed equivalent.",
                )
            )
    operating = plan.get("operating_economics", {})
    currency = operating.get("price_basis", {}).get("currency", "")
    for group, field, unit in [
        ("sales", "unit_price", currency + "/unit"),
        ("materials", "unit_price", currency + "/unit"),
        ("energy", "tariff_per_kwh", currency + "/kWh"),
        ("labour", "annual_base_salary", currency + "/FTE/year"),
        ("additional_expenses", "annual_allowance", currency + "/year"),
    ]:
        for i, row in enumerate(operating.get(group, [])):
            if field not in row or group == "sales" and (
                row.get("price_mode") != "assumed_price" or row.get("price_observation")
            ):
                continue
            add(
                ["operating_economics", group, i, field],
                f"{row.get('name', row.get('role', row.get('id', group)))} · {field.replace('_', ' ')}",
                (
                    currency + "/" + row.get("quantity_unit", "unit")
                    if group in {"sales", "materials"}
                    else unit
                ),
                row.get(field),
                row.get(field + "_low"), row.get(field + "_high"),
                source=str(row.get("source") or "Saved commercial/operating assumption"),
                rationale=str(row.get("rationale") or ""),
                kind="economic",
                hard_min=0,
            )
    for i, row in enumerate(operating.get("sales", [])):
        if row.get("price_mode") == "assumed_price":
            quote = row.get("price_observation") or {}
            if numeric(quote.get("discount_fraction")) is not None:
                add(
                    ["operating_economics", "sales", i, "price_observation", "discount_fraction"],
                    f"{row.get('name', 'Product')} · commercial discount",
                    "fraction",
                    quote["discount_fraction"], quote.get("discount_fraction_low"), quote.get("discount_fraction_high"),
                    source=str(quote.get("source_url") or "Saved selling-price observation"),
                    rationale=str(row.get("rationale") or ""), kind="economic", hard_min=0, hard_max=1,
                )
        if row.get("price_mode") == "cost_plus" and numeric(row.get("cost_markup_fraction")) is not None:
            add(
                ["operating_economics", "sales", i, "cost_markup_fraction"],
                f"{row.get('name', 'Product')} · cost-plus markup", "fraction",
                row["cost_markup_fraction"], row.get("cost_markup_fraction_low"), row.get("cost_markup_fraction_high"),
                source="Saved cost-plus assumption", rationale=str(row.get("rationale") or ""),
                kind="economic", hard_min=0,
            )
        for field, unit, limit in (
            ("allocation_fraction", "fraction", 1), ("saleable_fraction", "fraction", 1),
            ("sold_fraction", "fraction", 1), ("net_freight_deduction_per_unit", currency + "/unit", None),
            ("net_packaging_deduction_per_unit", currency + "/unit", None),
        ):
            if numeric(row.get(field)) is not None:
                add(
                    ["operating_economics", "sales", i, field],
                    f"{row.get('name', 'Product')} · {field.replace('_', ' ')}", unit,
                    row[field], row.get(field + "_low"), row.get(field + "_high"),
                    source="Saved product sales assumption", rationale=str(row.get("rationale") or ""),
                    kind="economic", hard_min=0, hard_max=limit,
                )
    for i, line in enumerate(operating.get("commercial_lines", [])):
        if line.get("included") is False:
            continue
        name = line.get("name", line.get("id", "Commercial payment"))
        unit = line.get("quantity_unit", "unit")
        period = {"monthly": "/month", "annual": "/year"}.get(line.get("rate_period"), "")
        targets = {}
        for j, year in enumerate(line.get("years", [])):
            for field, units, floor, ceiling in (
                ("rate", currency + "/" + unit + period, 0, None),
                ("fixed_payment", currency + "/year", 0, None),
                ("quantity", unit, 0, None),
                ("minimum_quantity", unit, 0, None),
                ("minimum_payment", currency + "/year", 0, None),
                ("availability", "fraction", 0, 1),
                ("escalation", "fraction/year", -.99, None),
            ):
                value = numeric(year.get(field))
                if value is None or field == "quantity" and line.get("stream_key"):
                    continue
                if value == 0 and field in {"rate", "fixed_payment", "minimum_quantity", "minimum_payment"}:
                    continue
                low = year.get(field + "_low", line.get(field + "_low"))
                high = year.get(field + "_high", line.get(field + "_high"))
                path = ["operating_economics", "commercial_lines", i, "years", j, field]
                key = field, value, numeric(low), numeric(high)
                if key in targets and len(targets[key].targets) < 100:
                    targets[key].targets.append(path)
                    continue
                targets[key] = add(
                    path, f"{name} · {field.replace('_', ' ')} (from year {year.get('year', j + 1)})",
                    units, value, low, high, source="Saved annual commercial terms",
                    rationale=str(line.get("rationale") or ""), kind="economic",
                    hard_min=floor, hard_max=ceiling,
                )
    for group, fields in (
        ("materials", (("annual_quantity_assumption", "/year", None),)),
        ("energy", (("efficiency", "fraction", 1), ("load_fraction", "fraction", 1))),
        ("labour", (("headcount_fte", "FTE", None), ("allocation_fraction", "fraction", 1))),
    ):
        for i, row in enumerate(operating.get(group, [])):
            for field, unit, ceiling in fields:
                if numeric(row.get(field)) is None or field == "annual_quantity_assumption" and row.get("stream_key"):
                    continue
                add(
                    ["operating_economics", group, i, field],
                    f"{row.get('name', row.get('role', row.get('id', group)))} · {field.replace('_', ' ')}",
                    str(row.get("quantity_unit") or "unit") + unit if unit == "/year" else unit,
                    row[field], row.get(field + "_low"), row.get(field + "_high"),
                    source="Saved operating assumption", rationale=str(row.get("rationale") or ""),
                    hard_min=0, hard_max=ceiling,
                )
    for i, row in enumerate(operating.get("energy", [])):
        if row.get("method") in {
            "thermal_duty",
            "shaft_power",
            "electrical_assumption",
        }:
            add(
                ["operating_economics", "energy", i, "power_kw"],
                f"{row.get('name', row['id'])} · duty",
                "kW",
                row.get("power_kw"),
                source=str(
                    row.get(
                        "rationale",
                        "Missing duty; requires engineering proposal or user input",
                    )
                ),
                kind="engineering",
                hard_min=0,
            )
    if operating:
        for field, unit, limit in [
            ("discount_rate", "fraction", 1),
            ("tax_rate", "fraction", 1),
        ]:
            add(
                ["operating_economics", "financial", field],
                field.replace("_", " "),
                unit,
                operating.get("financial", {}).get(field),
                source="Saved global financial assumption",
                kind="economic",
                hard_min=0,
                hard_max=limit,
            )
        for field, unit, limit in [
            ("days_per_year", "days/year", 366),
            ("hours_per_day", "h/day", 24),
        ]:
            add(
                ["operating_economics", "operating", field],
                field.replace("_", " "),
                unit,
                operating.get("operating", {}).get(field),
                source="Saved plant operating schedule",
                kind="economic",
                hard_min=0,
                hard_max=limit,
                strictly_positive=True,
            )
        for key, p in operating.get("garrett_factors", {}).items():
            from backend.opex.indexes.garrett.model import CATEGORIES

            definition = next((c for c in CATEGORIES if c.id == key), None)
            low = numeric(definition.minimum) if definition else None
            high = numeric(definition.maximum) if definition else None
            add(
                ["operating_economics", "garrett_factors", key, "fraction"],
                f"OPEX · {key.replace('_', ' ')}",
                "fraction",
                p.get("fraction"),
                p.get("low", low), p.get("high", high),
                auto_enable=False,
                source="Garrett Ch. 4 method range" if low is not None and high is not None else "Saved OPEX factor",
                rationale=str(p.get("rationale") or ""),
                kind="economic",
                hard_min=low if low is not None else 0,
                hard_max=high if high is not None else None,
            )
    from backend.capex import get_factor_ranges

    cap = plan.get("capex", {})
    try:
        ranges = {
            r["id"]: r
            for r in get_factor_ranges(
                cap.get("model_id", "garrett"), cap.get("process_type", "mixed")
            )
        }
    except ValueError:
        ranges = {}
    for key, value in cap.get("selected_factors", {}).items():
        factor = ranges.get(key, {})
        low, high = numeric(factor.get("minimum")), numeric(factor.get("maximum"))
        add(
            ["capex", "selected_factors", key],
            "CAPEX · " + key.replace("_", " "),
            "fraction",
            value,
            low, high,
            auto_enable=False,
            source="Saved capital-factor selection; published allowable ranges are not calibrated probabilities",
            rationale="Review distribution within the documented method limits",
            kind="economic",
            hard_min=low if low is not None else 0,
            hard_max=high,
        )
    for p in params:
        if p.targets[0][0] in state.get("locked", []):
            p.enabled = False
    # Identical electricity/utility tariffs share one sampled driver, not independent equipment prices.
    shared = {}
    result = []
    for p in params:
        path = p.targets[0]
        if (
            len(path) > 2
            and path[:2] == ["operating_economics", "energy"]
            and path[-1] == "tariff_per_kwh"
        ):
            row = operating["energy"][path[2]]
            key = (row.get("utility"), p.mode, p.unit)
            if key in shared:
                shared[key].targets.extend(p.targets)
                continue
            p.label = f"Global {row.get('utility', 'utility')} tariff"
            shared[key] = p
        result.append(p)
    suggested = {p["id"]: p for p in state.get("mc_assumption_proposals", [])}
    for i, p in enumerate(result):
        proposal = suggested.get(p.id)
        if (
            proposal
            and proposal.get("unit") == p.unit
            and proposal.get("targets") == p.targets
        ):
            # Proposals never alter approved/source values, and require explicit enablement.
            result[i] = p.model_copy(
                update={
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
                        "enabled",
                    )
                    if k in proposal
                }
            )
    lines = (
        (state.get("results") or {})
        .get("stages", {})
        .get("equipment", {})
        .get("result")
        or {}
    ).get("equipment", [])
    exceptions = [
        {
            "tag": r["equipment_tag"],
            "equipment_key": r.get("parsed_source", {}).get("equipment_key"),
            "candidate_models": r.get("decision", {}).get("candidate_curve_ids", []),
            "alias_of": r.get("decision", {}).get("alias_of"),
            "reason": r.get("decision", {}).get("rationale")
            or "; ".join(r.get("issues", [])),
            "status": (
                "alias_confirmation"
                if r.get("decision", {}).get("scope_decision") == "alias"
                else (
                    "unsupported_model"
                    if not r.get("decision", {}).get("candidate_curve_ids")
                    else "engineering_input_or_configuration"
                )
            ),
        }
        for r in lines
        if not priced_record(r)
        and not r.get("parsed_source", {}).get("confirmed_alias")
    ]
    return {
        "settings": Settings(
            parameters=result, baseline_revision=state.get("revision"),
            operating_years=operating.get("financial", {}).get("operating_years") or 20,
        ).model_dump(),
        "exceptions": exceptions,
        "equipment_count": len(entities),
        "baseline_operating_years": operating.get("financial", {}).get(
            "operating_years"
        ),
        "notice": "Stored low/high ranges are uncalibrated engineering assumptions. Missing ranges remain disabled. Normal/lognormal samples are bounded/truncated. Distribution shape and correlations require review. No external research or LLM was called.",
    }
