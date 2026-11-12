"""Source-native costing adapter; canonical conversion/escalation remain external."""

import json
from dataclasses import asdict, replace
from .registry import get_model, ROOT
from .evaluators import evaluate
from ...models import CostEstimate, positive
from ...unit_conversion import convert, Measurement, ConversionContext
from ..garrett.integrated import CostingResult
from ..garrett.installation import InstallationBreakdown


def native_input(value, unit, requirement, context=None, source=None):
    if requirement.get("manual_coordinate"):
        if unit != requirement["unit"]:
            raise ValueError(
                "MISSING_SIZING_INPUT: explicit composite design coordinate required in "
                + requirement["unit"]
            )
        return positive(value, "source design coordinate"), {
            "original_value": value,
            "original_unit": unit,
            "normalized_value": value,
            "normalized_unit": unit,
            "source": source or {},
            "status": "EXTRACTED" if source else "ASSUMED",
            "notice": "Explicit source-native coordinate; physical derivation not independently validated",
        }
    c = convert(value, unit, requirement["unit"], context=context, source=source or {})
    if c.value is None:
        raise ValueError("; ".join(c.issues))
    return positive(c.value, "model input"), asdict(c)


def estimate_cost(
    model_id,
    size,
    *,
    size_unit,
    unit_context=None,
    input_provenance=None,
    second_size=None,
    second_size_unit=None,
    second_input_provenance=None,
    allow_unverified=False,
    material=None,
    installation_profile=None,
    adjustment_basis_confirmed=False,
    operating_pressure=None,
    below_range_policy="minimum_size_floor",
    **options
):
    """below_range_policy (founder decision, 11 Nov 2026): "minimum_size_floor"
    (default) prices a primary size below the published lower bound at that bound,
    flagged as an explicit assumption; "extrapolate" keeps OpenPyTEA's strict
    refusal (OpenPyTEA never extrapolates). Sizes above the bound stay refused."""
    if below_range_policy not in {"minimum_size_floor", "extrapolate"}:
        raise ValueError("below_range_policy must be minimum_size_floor or extrapolate")
    m = get_model(model_id)
    if m["status"] == "disabled":
        raise ValueError("MODEL_DISABLED: " + "; ".join(m["disabled_reasons"]))
    unsupported = {k for k, v in options.items() if v is not None and v != []}
    if unsupported:
        raise ValueError(
            "Unsupported OpenPyTEA correction/options: "
            + ", ".join(sorted(unsupported))
        )
    req = m["input_requirements"]
    value, trace = native_input(size, size_unit, req[0], unit_context, input_provenance)
    v2 = None
    trace2 = None
    if len(req) > 1:
        if second_size is None or second_size_unit is None:
            raise ValueError(
                "MISSING_SIZING_INPUT: second independent model coordinate required: "
                + req[1]["role"]
            )
        v2, trace2 = native_input(
            second_size, second_size_unit, req[1], unit_context, second_input_provenance
        )
    elif second_size is not None:
        raise ValueError("Model does not accept a second coordinate")
    pressure_check = {"status": "not_supplied", "limit": m.get("pressure_limits")}
    if operating_pressure is not None:
        p = (
            Measurement(**operating_pressure)
            if isinstance(operating_pressure, dict)
            else operating_pressure
        )
        if not isinstance(p, Measurement):
            raise ValueError("Operating pressure must be a typed Measurement")
        limit = m.get("pressure_limits")
        if limit:
            pressure_context = replace(
                unit_context or ConversionContext(), target_pressure_basis="gauge"
            )
            c = convert(
                p.value,
                p.unit,
                limit["unit"],
                context=pressure_context,
                pressure_basis=p.pressure_basis,
                source=p.source,
            )
            if c.value is None:
                raise ValueError("; ".join(c.issues))
            if c.value > limit["maximum"]:
                raise ValueError(
                    "MODEL_CONDITION_OUT_OF_RANGE: pressure exceeds the source correlation limit"
                )
            pressure_check = {
                "status": "checked_supplied_pressure",
                "conversion": asdict(c),
                "limit": limit,
            }
        else:
            pressure_check = {
                "status": "source_limit_not_available",
                "supplied": asdict(p),
            }
    floor = None
    lower = m["raw"].get("s_lower", "")
    if below_range_policy == "minimum_size_floor" and lower not in ("", None) and value < float(lower):
        floor = {
            "policy": "minimum_size_floor",
            "requested_size": value,
            "priced_at_size": float(lower),
            "size_ratio": float(lower) / value,
            "size_unit": m["size_unit"],
            "basis": "Size below the correlation's published lower bound; priced at that bound (explicit preliminary-estimate assumption, not a validated small-equipment price).",
        }
    base = evaluate(m["raw"], floor["priced_at_size"] if floor else value, v2, allow_missing_bounds=allow_unverified)
    factors = json.loads((ROOT / "adjustment_factors.json").read_text(encoding="utf-8"))
    ratio = 1.0
    factor_details = {}
    if material is not None and material != m["default_material"]:
        if (
            adjustment_basis_confirmed is not True
            or m["cost_scope"] != "purchased_equipment"
        ):
            raise ValueError(
                "Material change requires explicit applicability confirmation and a purchased-equipment scope"
            )
        fm = factors["material_factors"]
        default = m["default_material"]
        if default not in fm or material not in fm:
            raise ValueError(
                "No supported relative material factor for this base/target material"
            )
        ratio = fm[material] / fm[default]
        factor_details = {
            "base_material": default,
            "selected_material": material,
            "relative_material_factor": ratio,
            "basis": "Pinned upstream generic factor ratio; user-confirmed applicability, provisional",
        }
    amount = base * ratio
    installation = None
    if m["cost_scope"] in {
        "purchased_equipment",
        "unit_price_per_ft",
        "unit_price_per_tray",
    }:
        installation = InstallationBreakdown(
            amount, None, None, None, "not_provided", {}
        )
        if installation_profile is not None:
            if (
                m["cost_scope"] != "purchased_equipment"
                or adjustment_basis_confirmed is not True
                or installation_profile not in factors["process_factors"]
            ):
                raise ValueError(
                    "Installation requires an explicit supported profile and applicability confirmation"
                )
            f = factors["process_factors"][installation_profile]
            direct = base * (
                (1 + f["fp"]) * ratio
                + sum(f[n] for n in ["fer", "fel", "fi", "fc", "fs", "fl"])
            )
            installation = InstallationBreakdown(
                amount,
                direct - amount,
                direct,
                direct / amount,
                "provisional",
                {
                    "source": "Pinned OpenPyTEA Equipment.process_factors; Towler & Sinnott (2022)",
                    "profile": installation_profile,
                    "factors": f,
                    "formula": "Cp_base*((1+fp)*relative_fm+fer+fel+fi+fc+fs+fl)",
                    "scope": "Separate installed estimate; CAPEX uses purchased component, not this total plus factorial charges",
                },
            )
    elif (
        installation_profile is not None
        or material is not None
        and material != m["default_material"]
    ):
        raise ValueError(
            "No extra generic installation/material adjustment allowed on installed/module/unit-price base costs"
        )
    notes = tuple(
        m["issues"]
        + [
            m["scope_note"],
            "Underlying source applicability, materials, pressure, temperature and auxiliaries require engineering review; mathematical parity is not design validation.",
        ]
        + (
            [
                "BELOW-RANGE FLOOR: priced at the published minimum size "
                + format(floor["priced_at_size"], ".4g") + " " + m["size_unit"]
                + " (requested " + format(value, ".4g") + ", "
                + format(floor["size_ratio"], ".3g") + "x smaller); list in the Basis of Estimate"
            ]
            if floor
            else []
        )
    )
    manifest = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    estimate = CostEstimate(
        m["equipment"],
        m["configuration"],
        amount,
        "USD",
        1.0,
        m["source_year"],
        value,
        m["size_unit"],
        m["cost_scope"],
        m["equation_family"] + ": " + str(m["coefficients"]),
        0,
        0,
        m["reference"],
        "OpenPyTEA cost_correlations.csv",
        manifest["files"]["cost_correlations.csv"],
        notes=notes,
        index_series="SOURCE_PRICE_BASIS",
    )
    evidence = {
        "source": "openpytea",
        "model_id": model_id,
        "upstream_key": m["upstream_key"],
        "model_metadata": m,
        "source_commit": manifest["commit"],
        "source_reference": m["reference"],
        "source_url": m["source_url"],
        "csv_line": m["csv_line"],
        "equation_family": m["equation_family"],
        "coefficients": m["coefficients"],
        "original_cost": base,
        "original_cost_year": m["source_year"],
        "input_classification": (input_provenance or {}).get("status", "ASSUMED"),
        "native_adjusted_cost": amount,
        "cost_basis": m["cost_scope"],
        "unit_conversion": trace,
        "second_input_conversion": trace2,
        "model_inputs": {
            "size": value,
            "size_unit": m["size_unit"],
            "second_size": v2,
            "second_size_unit": req[1]["unit"] if len(req) > 1 else None,
        },
        "material_adjustment": factor_details,
        "pressure_applicability": pressure_check,
        "scope_review_required": True,
        "applicability_status": "provisional",
        "input_provenance": input_provenance or {},
        "upstream_parallelisation": False,
        "upstream_escalation": False,
        "below_range_floor": floor,
    }
    return CostingResult(
        "provisional", estimate, base, notes, evidence, installation=installation
    )
