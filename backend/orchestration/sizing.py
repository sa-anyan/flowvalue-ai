"""Small explicit sizing adapters. LLM selects assumptions; Python performs arithmetic."""

from decimal import Decimal, InvalidOperation


def derive_size(proposal, report):
    sizing = proposal.get("sizing")
    if not sizing:
        return proposal.get("size"), proposal.get("size_unit"), None
    stream = next(
        (e for e in report["entities"] if e["key"] == sizing.get("stream_key")), None
    )
    if stream is None:
        raise ValueError("Sizing stream does not exist in engineering register")
    method = sizing.get("method")
    prop = "volume_flow" if method == "volume_residence" else sizing.get("property")
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
    if method == "volume_residence":
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
