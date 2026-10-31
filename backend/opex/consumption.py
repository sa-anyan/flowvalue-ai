"""Canonical source-observation selection and annual consumption; no inferred prices."""

from decimal import Decimal

from backend.equipment_costing.unit_conversion import convert


def decimal(value, *, minimum=0, maximum=None):
    if isinstance(value, bool):
        raise TypeError("Boolean is not an engineering quantity")
    result = Decimal(str(value))
    if (
        not result.is_finite()
        or minimum is not None
        and result < minimum
        or maximum is not None
        and result > maximum
    ):
        raise ValueError("Quantity outside declared bounds")
    return result


def observation(report, stream_key, property, component=None):
    entity = next((e for e in report["entities"] if e["key"] == stream_key), None)
    if entity is None:
        raise ValueError("Unknown engineering register reference: " + str(stream_key))
    matches = [
        v
        for v in entity["values"]
        if v["property"] == property
        and (
            str(v.get("component") or "").strip().casefold()
            == str(component or "").strip().casefold()
        )
        and v.get("normalized_value") is not None
        and v.get("status") != "unresolved"
    ]
    distinct = {
        (str(decimal(v["normalized_value"], minimum=None)), v.get("normalized_unit"))
        for v in matches
    }
    if len(distinct) != 1:
        raise ValueError(
            entity["identifier"] + ": no unambiguous " + property + " observation"
        )
    return matches[0]


def annual_consumption(
    report,
    *,
    stream_key,
    property,
    component,
    quantity_unit,
    operating_hours,
    throughput_fraction=1,
):
    v = observation(report, stream_key, property, component)
    target = quantity_unit + "/h"
    converted = convert(
        float(decimal(v["normalized_value"])),
        v["normalized_unit"],
        target,
        source={"evidence_id": v["id"], "worksheet": v["sheet"], "cell": v["cell"]},
    )
    if converted.value is None:
        raise ValueError(
            "Consumption conversion unresolved: " + "; ".join(converted.issues)
        )
    hours = decimal(operating_hours, maximum=8784)
    fraction = decimal(throughput_fraction, maximum=1)
    return {
        "annual_quantity": decimal(converted.value) * hours * fraction,
        "quantity_unit": quantity_unit + "/year",
        "hourly_quantity": decimal(converted.value),
        "hourly_unit": target,
        "source_evidence": v,
        "conversion": converted,
        "operating_hours": hours,
        "throughput_fraction": fraction,
    }
