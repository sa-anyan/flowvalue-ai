"""Minimum-size floor record shared by the Nottingham and additional models.

Founder decision (11 Nov 2026, option B): a size below a correlation's
published lower bound is priced at that bound and recorded as an explicit
preliminary-estimate assumption. Garrett and OpenPyTEA build the same record
in their own adapters.
"""


def minimum_size_floor(requested, lower, unit):
    return {
        "policy": "minimum_size_floor",
        "requested_size": requested,
        "priced_at_size": float(lower),
        "size_ratio": float(lower) / requested,
        "size_unit": unit,
        "basis": "Size below the correlation's published lower bound; priced at that bound (explicit preliminary-estimate assumption, not a validated small-equipment price).",
    }


def floor_issue(floor, bound_name):
    return (
        "BELOW-RANGE FLOOR: priced at the "
        + bound_name
        + " "
        + format(floor["priced_at_size"], ".4g")
        + " "
        + floor["size_unit"]
        + " (requested "
        + format(floor["requested_size"], ".4g")
        + ", "
        + format(floor["size_ratio"], ".3g")
        + "x smaller); list in the Basis of Estimate"
    )
