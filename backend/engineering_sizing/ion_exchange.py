"""Preliminary ion-exchange bed/vessel envelope; not resin exhaustion design."""

from .common import positive


def calculate(flow, inputs):
    q = positive(flow, "service flow m3/h")
    minutes = positive(
        inputs.get("empty_bed_contact_time_min"), "empty-bed contact time min"
    )
    fraction = positive(inputs.get("resin_bed_fraction"), "resin bed fraction")
    if fraction > 1:
        raise ValueError("Resin bed fraction cannot exceed one")
    bed = q * minutes / 60
    return (
        bed / fraction,
        "m3",
        {
            "formula": "V_bed = Q * EBCT_minutes / 60; V_vessel = V_bed / resin_bed_fraction",
            "resin_bed_volume_m3": bed,
            "limitation": "Preliminary EBCT scenario only; ionic load, resin capacity, regeneration cycle and freeboard require independent checks.",
        },
    )


def capacity_sizing(flow, inputs):
    """Capacity-based bed envelope with explicit equivalent-load and cycle assumptions."""
    q = positive(flow, "service flow m3/h")
    load = positive(
        inputs.get("ionic_load_mol_equiv_m3"), "feed ionic equivalents mol/m3"
    )
    cycle = positive(inputs.get("service_cycle_h"), "hours between regenerations")
    capacity = positive(
        inputs.get("working_resin_capacity_mol_equiv_m3"),
        "working resin capacity mol equivalents/m3",
    )
    fraction = positive(inputs.get("resin_bed_fraction"), "resin vessel fraction")
    if fraction > 1:
        raise ValueError("Resin bed fraction cannot exceed one")
    bed = q * load * cycle / capacity
    return (
        bed / fraction,
        "m3",
        {
            "formula": "V_bed = Q * feed_equivalent_concentration * service_cycle / working_capacity; V_vessel = V_bed / bed_fraction",
            "resin_bed_volume_m3": bed,
            "regeneration_load_mol_equivalents": q * load * cycle,
            "limitation": "Working capacity must match resin, species, competing ions and breakthrough target. Regenerant type, stoichiometry, efficiency, backwash and neutralisation costs remain separate explicit inputs.",
        },
    )
