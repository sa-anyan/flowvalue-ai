"""Explicit production/productivity scenario; no inferred physical stream links.

Rates are supplied assumptions or referenced project requirements. This does not
establish kinetics, gas transfer, yield, vessel geometry or a validated design.
"""

from backend.engineering_sizing.common import positive
from backend.engineering_sizing.versioning import method_metadata


def vessel_productivity(inputs):
    metadata = method_metadata(
        "vessel_productivity", vessel_productivity, execution_layer="supplemental"
    )
    production = positive(inputs.get("product_rate_kg_h"), "product rate kg/h")
    productivity = positive(
        inputs.get("volumetric_productivity_kg_m3_h"), "volumetric productivity kg/m3/h"
    )
    allocation = positive(
        inputs.get("production_allocation_fraction"), "production allocation"
    )
    working = positive(inputs.get("working_fraction"), "working fraction")
    if allocation > 1 or working > 1:
        raise ValueError("Production allocation and working fractions must be <= 1")
    return (
        production * allocation / productivity / working,
        "m3",
        {
            "engineering_method": metadata,
            "formula": "V_design = product_rate * production_allocation / volumetric_productivity / working_fraction",
            "scope": "Explicit preliminary production/productivity scenario; no workbook flow or connection is created. Does not validate biological kinetics, mass transfer, residence time, capacity or complete bioreactor package scope.",
        },
    )
