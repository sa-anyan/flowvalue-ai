"""Small explicit sizing adapters. LLM selects assumptions; Python performs arithmetic."""

from decimal import Decimal, InvalidOperation


def derive_size(proposal, report):
    sizing = proposal.get("sizing")
    if not sizing:
        if proposal.get("size") is not None:
            return proposal.get("size"), proposal.get("size_unit"), None
        if proposal.get("curve_id"):
            from backend.equipment_costing.registry import list_equipment_models

            model = next(
                (m for m in list_equipment_models(source="all") if m["id"] == proposal["curve_id"]),
                None,
            )
            if model:
                quantity = model["input_requirements"][0]["quantity"]
                entity = next(
                    (
                        e
                        for e in report["entities"]
                        if e["key"] == proposal.get("equipment_key")
                    ),
                    None,
                )
                prop = {
                    "volume": "volume",
                    "area": "area",
                    "power": "power",
                    "mass_flow": "mass_flow",
                    "volume_flow": "volume_flow",
                }.get(quantity)
                observations = [
                    v
                    for v in (entity or {}).get("values", [])
                    if v["property"] == prop
                    and v.get("normalized_value") is not None
                    and v.get("status") != "unresolved"
                ]
                if (
                    len(
                        {
                            (str(v["normalized_value"]), v.get("normalized_unit"))
                            for v in observations
                        }
                    )
                    == 1
                ):
                    v = observations[0]
                    return (
                        float(v["normalized_value"]),
                        v["normalized_unit"],
                        {
                            "method": "supplied_dimension",
                            "source_evidence": [v["id"]],
                            "status": "source_supported_not_design_validation",
                        },
                    )
        return None, proposal.get("size_unit"), None
    sizing = dict(sizing)
    parameters = sizing.get("parameters", {})
    for name in ("density_kg_m3", "residence_time_h", "working_fraction"):
        if name in parameters:
            sizing[name] = parameters[name]["value"]
    from backend.engineering_sizing.registry import METHODS

    if sizing.get("method") in METHODS:
        from backend.engineering_sizing.adapter import derive
        from backend.engineering_sizing.registry import PARAMETER_UNITS

        parameters = dict(parameters)
        for name in ("density_kg_m3", "residence_time_h", "working_fraction"):
            if name not in parameters and sizing.get(name) is not None:
                parameters[name] = {
                    "value": sizing[name],
                    "unit": PARAMETER_UNITS[name][0],
                    "status": "llm_estimate",
                    "rationale": "Explicit named-unit engineering parameter",
                }
        sizing["parameters"] = parameters
        return derive(sizing, report)
    stream = next(
        (e for e in report["entities"] if e["key"] == sizing.get("stream_key")), None
    )
    if stream is None:
        raise ValueError("Sizing stream does not exist in engineering register")
    method = sizing.get("method")
    prop = (
        "mass_flow"
        if method in {"mass_residence", "mass_to_volume_flow"}
        else "volume_flow"
        if method == "volume_residence"
        else sizing.get("property")
    )
    matches = [
        v
        for v in stream["values"]
        if v["property"] == prop
        and not v.get("component")
        and v.get("normalized_value") is not None
        and v.get("status") != "unresolved"
    ]
    distinct = {(str(v["normalized_value"]), v.get("normalized_unit")) for v in matches}
    if len(distinct) != 1:
        raise ValueError(
            "Sizing needs an unambiguous total " + str(prop) + " observation"
        )
    value = Decimal(str(matches[0]["normalized_value"]))
    unit = matches[0]["normalized_unit"]
    evidence = {
        "method": method,
        "stream_key": stream["key"],
        "source_evidence": matches[0]["id"],
        "assumptions": sizing,
        "status": "preliminary engineering scenario",
    }
    if method == "stream_property":
        return float(value), unit, evidence
    if method in {"mass_residence", "mass_to_volume_flow"}:
        if unit != "kg/h":
            raise ValueError(
                "Mass-based volume sizing requires total mass flow in kg/h"
            )
        try:
            density = Decimal(str(sizing["density_kg_m3"]))
        except (KeyError, InvalidOperation) as exc:
            raise ValueError(
                "Explicit density assumption in kg/m3 is required"
            ) from exc
        if not density.is_finite() or density <= 0:
            raise ValueError("Density must be finite and positive")
        value = value / density
        unit = "m3/h"
        if method == "mass_to_volume_flow":
            return float(value), unit, evidence
    if method in {"volume_residence", "mass_residence"}:
        if unit != "m3/h":
            raise ValueError(
                "Residence sizing requires normalised volumetric flow in m3/h"
            )
        try:
            residence = Decimal(str(sizing["residence_time_h"]))
            fraction = Decimal(str(sizing["working_fraction"]))
        except (KeyError, InvalidOperation) as exc:
            raise ValueError(
                "Explicit residence time and working-volume fraction required"
            ) from exc
        if (
            not residence.is_finite()
            or not fraction.is_finite()
            or residence <= 0
            or not 0 < fraction <= 1
        ):
            raise ValueError(
                "Positive residence time and working fraction (0,1] required"
            )
        return float(value * residence / fraction), "m3", evidence
    raise ValueError("No Python sizing method exists for " + str(method))
