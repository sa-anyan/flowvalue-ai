"""Read-only engineering diagnostics; never repair source values or certify topology."""

from decimal import Decimal, InvalidOperation


def process_sheets(report):
    """Explicit scope wins; otherwise use sheets tied to registered equipment.

    Other sheets are unassigned, not automatically excluded from the project.
    With no equipment/scope evidence, retain the entire source for review.
    """
    decisions = (report.get("calculation_scope") or {}).get("worksheets") or []
    active = {d["sheet"] for d in decisions if d.get("role") == "active"}
    if active:
        return active, True
    entities = report.get("entities") or []
    equipment = [e for e in entities if e.get("kind") == "equipment"]
    sheets = {(e.get("id_evidence") or {}).get("sheet") for e in equipment}
    linked = {k for e in equipment for k in e.get("stream_keys", [])}
    linked.update(c.get("stream_key") for c in report.get("connections", [])
                  if c.get("equipment_key") in {e.get("key") for e in equipment})
    sheets.update((e.get("id_evidence") or {}).get("sheet")
                  for e in entities if e.get("key") in linked)
    return sheets - {None}, False


def balance_summary(report):
    sheets, explicit = process_sheets(report)
    streams = [e for e in report.get("entities", []) if e.get("kind") == "material"
               and (not sheets or (e.get("id_evidence") or {}).get("sheet") in sheets)]
    mismatches = []
    for stream in streams:
        values = stream.get("values") or []
        totals = [v for v in values if v.get("property") == "mass_flow" and not v.get("component")]
        for total in totals:
            if not total.get("normalized_unit"):
                continue
            parts = [v for v in values if v.get("property") == "component_mass_flow"
                     and v.get("component") and v.get("normalized_unit") == total.get("normalized_unit")]
            try:
                amount = Decimal(str(total.get("normalized_value")))
                components = [Decimal(str(v.get("normalized_value"))) for v in parts]
            except InvalidOperation:
                continue
            if not components or not amount.is_finite() or not all(v.is_finite() for v in components):
                continue
            summed = sum(components)
            if abs(summed - amount) > max(Decimal("0.000001"), abs(amount) * Decimal("0.000001")):
                mismatches.append({"stream": stream.get("identifier"),
                                   "source": f"{total.get('sheet')}!{total.get('cell')}",
                                   "reported": str(amount), "component_sum": str(summed),
                                   "difference": str(summed - amount), "unit": total.get("normalized_unit")})
    checks = report.get("checks") or []
    def status(name):
        selected = [c for c in checks if c.get("name") == name]
        if any(c.get("residual") is not None and c.get("status") != "verified" for c in selected):
            return "imbalanced"
        if selected and all(c.get("status") == "verified" for c in selected):
            return "verified"
        return "unverified"
    mass, energy = status("Overall mass balance"), status("Energy balance")
    if mismatches:
        mass = "inconsistent"
    notes = []
    if mass != "verified":
        notes.append("Overall mass closure is not verified. A complete boundary and consistent source flows are required.")
    if energy != "verified":
        notes.append("Energy closure is not verified. Complete enthalpy, heat and work terms on a common basis are required.")
    outside = sorted({(e.get("id_evidence") or {}).get("sheet") for e in report.get("entities", [])
                      if e.get("kind") == "material"} - sheets - {None}) if sheets else []
    if outside and not explicit:
        notes.append("Additional worksheets are not linked to the equipment register; confirm their scope: " + ", ".join(outside) + ".")
    return {"mass": mass, "energy": energy, "mismatches": mismatches, "notes": notes,
            "worksheets": sorted(sheets), "source_values_changed": False}


def project_status(state):
    """Refresh diagnostics for saved runs without changing approvals or results."""
    report = state.get("scoped_report") or state.get("effective_report")
    if not report:
        return state
    state["balance_summary"] = balance_summary(report)
    equipment = ((state.get("results") or {}).get("stages") or {}).get("equipment") or {}
    coverage = (equipment.get("result") or {}).get("pricing_coverage")
    if coverage is not None:
        completeness = refresh_scope_notes(report, coverage.get("register_completeness") or {}, state.get("plan") or {})
        coverage["register_completeness"] = completeness
        tiers = coverage.get("tiers") or {}
        if completeness["possibly_missing"]:
            tiers["register_completeness"] = "unconfirmed: " + ", ".join(i["label"] for i in completeness["possibly_missing"])
        else:
            tiers.pop("register_completeness", None)
        # Scope review still prevents claiming complete whole-project coverage.
        if completeness.get("scope_review"):
            coverage["complete"] = False
            tiers["meets_coverage_target_without_assumptions"] = False
    return state


def refresh_scope_notes(report, previous, plan):
    """Reclassify evidenced off-sheet warnings, preserving saved review decisions."""
    from backend.equipment_resolution.register_completeness import check

    current = check(report, plan=plan)
    if not previous:
        return current
    sheets, explicit = process_sheets(report)
    moved, retained = [], []
    for item in previous.get("possibly_missing", []):
        sources = [e.get("source") for e in item.get("evidence", [])]
        off_sheet = bool(sheets and sources) and all(
            source and "!" in source and source.rsplit("!", 1)[0] not in sheets for source in sources)
        if off_sheet:
            if not explicit:
                moved.append(item)
        else:
            retained.append(item)
    retained = list({i["family"]: i for i in [*retained, *current["possibly_missing"]]}.values())
    # Saved exclusions/reviews remain auditable even when there is no longer a
    # matching source mention. Only off-sheet missing-unit claims are changed.
    result = dict(previous, possibly_missing=retained)
    notes = {i["family"]: i for i in [*moved, *current.get("scope_review", [])]}
    result["scope_review"] = list(notes.values())
    result["status"] = "unconfirmed" if retained else "scope_review_required" if notes else "no_unregistered_units_named"
    if not retained:
        result["notice"] = ("Additional worksheets need scope confirmation; units named there are not counted as missing process equipment."
                            if notes else "No unregistered equipment families named in the reviewed process scope.")
    return result
