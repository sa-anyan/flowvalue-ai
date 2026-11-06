"""Pinned, validated catalogue. All imported rows remain inspectable."""

import copy, csv, json, math, re
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote
from .evaluators import coefficients
from .metadata import coordinate, cost_scope

ROOT = Path(__file__).parent


def model_id(key):
    return "openpytea:" + quote(key, safe="._-")


@lru_cache(maxsize=1)
def catalogue():
    rows = list(csv.DictReader((ROOT / "correlations.csv").open(encoding="utf-8-sig")))
    result = {}
    for line, row in enumerate(rows, 2):
        issues = []
        disabled = []
        key = row["key"]
        identifier = model_id(key)
        if not key.strip() or identifier in result:
            raise ValueError("Duplicate/empty upstream model key")
        try:
            form, c = coefficients(row)
            for lo, hi in [("s_lower", "s_upper"), ("s2_lower", "s2_upper")]:
                values = [float(row[n]) for n in (lo, hi) if row[n] != ""]
                if any(not math.isfinite(v) or v < 0 for v in values) or (
                    len(values) == 2 and values[0] > values[1]
                ):
                    raise ValueError("Invalid capacity bounds")
            if not row["cost_year"].isdigit() or not row["source"] or not row["units"]:
                raise ValueError("Missing source year/reference/unit")
        except (ValueError, KeyError, TypeError) as exc:
            disabled.append(str(exc))
            form = row.get("form")
            c = {}
        inputs = coordinate(row["units"])
        if form == "2-var power-law" and len(inputs) != 2:
            disabled.append("Two-variable sizing contract unresolved")
        scope = cost_scope(row)
        if scope == "unresolved":
            disabled.append(
                "Cost scope not explicit in upstream Remarks; cannot assume purchased equipment"
            )
        if "poundsterlling" in row.get("notes", ""):
            disabled.append(
                "Source notes original GBP; dataset USD conversion basis unverified"
            )
        if not row["s_lower"] or not row["s_upper"]:
            issues.append("Published first-coordinate bounds missing")
        if any(i["manual_coordinate"] for i in inputs):
            issues.append(
                "Composite/source-specific coordinate needs explicit native design input; no automatic derivation"
            )
        if row.get("", ""):
            issues.append("Nonempty unnamed upstream CSV column preserved")
        if (
            "precise 2013 annual average = 567." in row.get("notes", "")
            and "567.3" not in row["notes"]
        ):
            issues.append("Conflicting upstream CEPCI note; not used as an index")
        pressure_match = re.search(
            r"pressures? (?:up to|to) (\d+(?:\.\d+)?) psig", row["Remarks"], re.I
        )
        pressure_limits = (
            {
                "maximum": float(pressure_match[1]),
                "unit": "psig",
                "basis": "gauge",
                "source_text": row["Remarks"],
            }
            if pressure_match
            else None
        )
        requirements = [
            dict(
                name="size" if j == 0 else "second_size",
                quantity=i["quantity"],
                unit=i["unit"],
                required=True,
                role=i["role"],
                manual_coordinate=i["manual_coordinate"],
            )
            for j, i in enumerate(inputs)
        ]
        result[identifier] = dict(
            id=identifier,
            upstream_key=key,
            source="openpytea",
            category=row["category"],
            equipment=row["category"] + " / " + row["type"],
            configuration=row["type"],
            aliases=[row["type"]],
            size_unit=inputs[0]["unit"],
            input_requirements=requirements,
            capacity_limits=[row["s_lower"] or None, row["s_upper"] or None],
            secondary_capacity_limits=[
                row["s2_lower"] or None,
                row["s2_upper"] or None,
            ],
            source_year=row["cost_year"],
            currency="USD",
            currency_basis="Upstream equipment guide states USD; original notes retained",
            cost_scope=scope,
            default_material=row["default material"],
            pressure_limits=pressure_limits,
            equation_family=form,
            coefficients=c,
            reference=row["source"],
            source_url=row["doi /  link"],
            scope_note=row["Remarks"],
            notes=row["notes"],
            raw=row,
            csv_line=line,
            status="disabled" if disabled else "available_provisional",
            disabled_reasons=disabled,
            issues=issues,
            limitation="; ".join(disabled + issues + [row["Remarks"], row["notes"]]),
            automatically_sizeable=False,
            sizing_status=(
                "manual_coordinate_required"
                if any(i["manual_coordinate"] for i in inputs)
                else "measurement_or_explicit_engineering_assumptions_required"
            ),
        )
    return result


def list_models():
    return copy.deepcopy(list(catalogue().values()))


def get_model(identifier):
    try:
        return copy.deepcopy(catalogue()[identifier])
    except KeyError as exc:
        raise ValueError("Unknown OpenPyTEA model") from exc
