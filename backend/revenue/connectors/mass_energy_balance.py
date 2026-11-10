"""Source-backed annual billable quantities; no physical values supplied by AI."""

from backend.opex.consumption import annual_consumption


def annual_billable(report, line, hours, ramp):
    if line["category"] == "capacity_availability":
        raise ValueError(
            "Reservation capacity is not annual throughput; supply an explicit contracted capacity quantity"
        )
    if line.get("manual_rate"):
        from ..indexes.openpytea.rate_model import annual_manual_quantity

        return annual_manual_quantity(line, hours, ramp)
    return annual_consumption(
        report,
        stream_key=line["stream_key"],
        property=line["property"],
        component=line.get("component"),
        quantity_unit=line["quantity_unit"],
        operating_hours=hours,
        throughput_fraction=ramp,
    )
