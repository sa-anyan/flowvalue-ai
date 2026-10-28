"""Conservative checks: explicit boundary and regime are prerequisites for closure."""

import re
from collections import defaultdict
from math import isclose

from .models import BalanceReport, Check, Issue
from .units import clean


def one(entity, prop, component=None):
    values = [
        v for v in entity.values if v.property == prop and v.component == component
    ]
    valid = [
        v for v in values if v.status != "unresolved" and v.normalized_value is not None
    ]
    if not valid:
        return None
    first = valid[0]
    if any(
        (v.normalized_unit, v.normalized_value)
        != (first.normalized_unit, first.normalized_value)
        for v in valid
    ):
        return None
    return first


def validate(report: BalanceReport):
    def issue(code, msg, ids=()):
        report.issues.append(Issue(code=code, message=msg, evidence_ids=list(ids)))

    material = [e for e in report.entities if e.kind == "material"]
    equipment = {e.identifier for e in report.entities if e.kind == "equipment"}
    grouped = defaultdict(list)
    for e in report.entities:
        grouped[e.kind, e.case, e.identifier].append(e)
        for p in ("source", "destination"):
            v = one(e, p)
            if (
                v
                and str(v.normalized_value) not in equipment
                and clean(v.normalized_value)
                not in (
                    "source",
                    "sink",
                    "feed",
                    "product",
                    "waste",
                    "boundary",
                    "outside",
                    "environment",
                )
            ):
                issue(
                    "unresolved_connection",
                    f"{e.identifier}: {p} {v.normalized_value} is not a declared equipment tag; connection remains unresolved.",
                    [v.id],
                )
        if e.kind == "material":
            missing = [
                p
                for p in ("mass_flow", "temperature", "pressure", "phase")
                if one(e, p) is None
            ]
            if missing:
                issue(
                    "incomplete_stream",
                    f"{e.identifier} [{e.case or 'unspecified case'}]: missing or unresolved "
                    + ", ".join(missing),
                    [e.id_evidence.id],
                )
        for basis in ("mass_fraction", "mole_fraction"):
            fractions = [v for v in e.values if v.property == basis and v.component]
            if fractions:
                total = sum(
                    float(v.normalized_value)
                    for v in fractions
                    if isinstance(v.normalized_value, (int, float))
                )
                if all(v.status != "unresolved" for v in fractions) and not isclose(
                    total, 1, rel_tol=1e-4, abs_tol=1e-6
                ):
                    issue(
                        "composition_sum",
                        f"{e.identifier}: listed {basis} values sum to {total:g}, not 1. Completeness/basis needs confirmation.",
                        [v.id for v in fractions],
                    )
    stream_ids = {e.identifier for e in material}
    for e in report.entities:
        if e.kind != "equipment":
            continue
        for prop, endpoint in (("inlets", "destination"), ("outlets", "source")):
            v = one(e, prop)
            if not v:
                continue
            raw = str(v.normalized_value)
            identifiers = (
                [raw]
                if raw in stream_ids
                else [x.strip() for x in re.split(r"[,;]", raw) if x.strip()]
            )
            for ident in identifiers:
                matching = [stream for stream in material if stream.identifier == ident]
                if not matching:
                    issue(
                        "unresolved_equipment_stream",
                        f"{e.identifier}: declared {prop} stream {ident} is absent from material records.",
                        [v.id],
                    )
                    continue
                for stream in matching:
                    actual = one(stream, endpoint)
                    if actual and str(actual.normalized_value) != e.identifier:
                        issue(
                            "connection_conflict",
                            f"{e.identifier}: {prop} lists {ident}, but stream {endpoint} is {actual.normalized_value}. Both observations retained.",
                            [v.id, actual.id],
                        )
                    elif actual is None:
                        issue(
                            "unresolved_equipment_stream",
                            f"{ident}: no {endpoint} field to corroborate equipment {prop} for {e.identifier}.",
                            [v.id],
                        )
    for (_, case, ident), records in grouped.items():
        tables = [e.table for e in records]
        if len(tables) != len(set(tables)):
            issue(
                "duplicate_identifier",
                f"{ident} [{case or 'unspecified case'}]: duplicate identifiers within one table; records retained separately.",
                [e.id_evidence.id for e in records],
            )
        by_property = defaultdict(list)
        for e in records:
            for v in e.values:
                if v.status != "unresolved":
                    by_property[v.property, v.component].append(v)
        for (p, _), vs in by_property.items():
            if len({(v.normalized_value, v.normalized_unit) for v in vs}) > 1:
                issue(
                    "conflicting_values",
                    f"{ident} [{case or 'unspecified case'}]: conflicting {p} observations; no value was chosen automatically.",
                    [v.id for v in vs],
                )
    declaration_values = defaultdict(set)
    for d in report.declarations:
        if d.status == "verified":
            declaration_values[clean(d.label)].add(clean(d.normalized_value))
    declarations = {
        key: next(iter(values))
        for key, values in declaration_values.items()
        if len(values) == 1
    }
    for key, values in declaration_values.items():
        if len(values) > 1:
            issue(
                "conflicting_declarations",
                f"Conflicting {key} declarations; none used for closure.",
            )
    basis = declarations.get(
        "mass balance basis", declarations.get("balance basis", "")
    )
    complete = "steady" in basis and "complete boundary" in basis
    cases = {e.case for e in material} or {""}
    for case in sorted(cases):
        records = [e for e in material if e.case == case]
        # Any duplicate ID in this case blocks closure rather than summing observations twice.
        unique = len({e.identifier for e in records}) == len(records)
        sides = {"inlet": [], "outlet": []}
        unknown = []
        for e in records:
            direction = one(e, "direction")
            d = clean(direction.normalized_value) if direction else ""
            if d in ("in", "feed", "inlet", "input"):
                sides["inlet"].append(e)
            elif d in ("out", "product", "outlet", "output"):
                sides["outlet"].append(e)
            elif d != "internal":
                unknown.append(e)
        scope = case or "unspecified operating case"
        boundary = sides["inlet"] + sides["outlet"]
        flows = [one(e, "mass_flow") for e in boundary]
        ids = [v.id for v in flows if v]
        ready = (
            complete
            and unique
            and not unknown
            and bool(sides["inlet"])
            and bool(sides["outlet"])
            and all(v is not None and v.status == "verified" for v in flows)
        )
        if not ready:
            missing = []
            if not complete:
                missing.append("explicit steady-state complete-boundary declaration")
            if not unique:
                missing.append("unique stream identifiers across this case")
            if unknown or not boundary:
                missing.append(
                    "inlet/outlet/internal boundary classifications for every stream"
                )
            if not sides["inlet"] or not sides["outlet"]:
                missing.append("both boundary inlet and outlet streams")
            if any(v is None or v.status != "verified" for v in flows):
                missing.append(
                    "confirmed mass flows with compatible units (formula caches and synthetic values need confirmation)"
                )
            report.checks.append(
                Check(
                    name="Overall mass balance",
                    scope=scope,
                    message="Cannot verify: " + "; ".join(missing),
                    evidence_ids=ids,
                )
            )
        else:
            incoming = sum(
                float(one(e, "mass_flow").normalized_value) for e in sides["inlet"]
            )
            outgoing = sum(
                float(one(e, "mass_flow").normalized_value) for e in sides["outlet"]
            )
            residual = incoming - outgoing
            ok = isclose(incoming, outgoing, rel_tol=1e-4, abs_tol=1e-6)
            report.checks.append(
                Check(
                    name="Overall mass balance",
                    scope=scope,
                    status="verified" if ok else "unresolved",
                    message="Arithmetic closes for workbook-declared steady-state complete boundary."
                    if ok
                    else "Declared boundary does not close; source data was not corrected.",
                    residual=residual,
                    unit="kg/h",
                    evidence_ids=ids,
                )
            )
        components = {
            v.component
            for e in boundary
            for v in e.values
            if v.component and v.property in ("mass_flow", "mass_fraction")
        }
        nonreacting = "nonreacting" in declarations.get("component balance basis", "")
        for component in sorted(components):
            cvalues = []
            for e in boundary:
                v = one(e, "mass_flow", component)
                f = one(e, "mass_fraction", component)
                m = one(e, "mass_flow")
                if v and v.status == "verified":
                    cvalues.append((float(v.normalized_value), [v.id]))
                elif f and m and f.status == m.status == "verified":
                    cvalues.append(
                        (
                            float(f.normalized_value) * float(m.normalized_value),
                            [f.id, m.id],
                        )
                    )
                else:
                    cvalues.append(None)
            if ready and nonreacting and all(v is not None for v in cvalues):
                n = len(sides["inlet"])
                i = sum(v[0] for v in cvalues[:n])
                o = sum(v[0] for v in cvalues[n:])
                ok = isclose(i, o, rel_tol=1e-4, abs_tol=1e-6)
                report.checks.append(
                    Check(
                        name=f"Component mass: {component}",
                        scope=scope,
                        status="verified" if ok else "unresolved",
                        message="Nonreacting declared-boundary arithmetic closes."
                        if ok
                        else "Component residual is outside tolerance; no correction made.",
                        residual=i - o,
                        unit="kg/h",
                        evidence_ids=[j for v in cvalues for j in v[1]],
                    )
                )
            else:
                report.checks.append(
                    Check(
                        name=f"Component mass: {component}",
                        scope=scope,
                        message="Needs complete boundary flows/compositions and explicit nonreacting basis. Reaction generation/consumption is not inferred.",
                    )
                )
        if not components:
            report.checks.append(
                Check(
                    name="Component mass balances",
                    scope=scope,
                    message="No complete, explicitly based component mass-flow/fraction inventory. Reaction sources/sinks are not inferred.",
                )
            )
        energy_basis = declarations.get("energy balance basis", "")
        sign = declarations.get("energy sign convention", "")
        hs = [one(e, "enthalpy_flow") for e in boundary]
        energy = [e for e in report.entities if e.kind == "energy" and e.case == case]
        duties = [
            v
            for e in energy
            for v in e.values
            if v.property in ("heat_added", "heat_removed", "work_in", "work_out")
        ]
        # Requires affirmative exclusions for terms not represented; never assume missing heat/work is zero.
        er = (
            ready
            and "steady" in energy_basis
            and "complete boundary" in energy_basis
            and "kinetic and potential negligible" in energy_basis
            and "common enthalpy reference" in energy_basis
            and "positive into boundary" in sign
            and all(h and h.status == "verified" for h in hs)
            and len(hs) > 0
            and bool(energy)
            and bool(duties)
            and {v.property for v in duties}
            == {"heat_added", "heat_removed", "work_in", "work_out"}
            and len({e.identifier for e in energy}) == len(energy)
            and all(v.status == "verified" for v in duties)
        )
        if er:
            n = len(sides["inlet"])
            terms = sum(
                float(v.normalized_value)
                * (1 if v.property in ("heat_added", "work_in") else -1)
                for v in duties
            )
            incoming = sum(float(v.normalized_value) for v in hs[:n])
            outgoing = sum(float(v.normalized_value) for v in hs[n:])
            residual = incoming + terms - outgoing
            # Verify every energy record has exactly the explicitly supported terms.
            if any(
                not any(v in duties for v in e.values)
                or any(
                    v.property in ("heat_duty", "electrical_power") for v in e.values
                )
                for e in energy
            ):
                er = False
            if er:
                report.checks.append(
                    Check(
                        name="Energy balance",
                        scope=scope,
                        status="verified"
                        if abs(residual)
                        <= max(
                            1e-6, 1e-4 * max(abs(incoming), abs(outgoing), abs(terms))
                        )
                        else "unresolved",
                        message="Declared boundary enthalpy plus explicitly signed heat/work arithmetic; common enthalpy reference remains workbook responsibility.",
                        residual=residual,
                        unit="kW",
                        evidence_ids=[v.id for v in hs + duties],
                    )
                )
        if not er:
            report.checks.append(
                Check(
                    name="Energy balance",
                    scope=scope,
                    message="Needs complete steady-state boundary, all enthalpy-flow terms on a common reference, explicit heat/work terms (including zeroes), sign convention and kinetic/potential-energy treatment. Electrical demand alone is not an energy balance.",
                )
            )
    if not material:
        issue(
            "missing_material_streams",
            "No supported material stream table. Equipment/load ledgers alone do not establish a mass or energy balance.",
        )
