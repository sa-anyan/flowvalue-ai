"""Filter area from explicit volumetric hydraulic loading; not a universal cake model."""

from .common import positive as p


def calculate(flow, inputs):
    q = p(flow, "volumetric flow m3/h")
    loading = p(inputs.get("hydraulic_loading_m_h"), "hydraulic loading m3/m2/h")
    return (
        q / loading,
        "m2",
        {
            "formula": "A = Q / hydraulic_loading",
            "scope": "Explicit hydraulic screening assumption; solids/cake/cycle constraints may govern",
        },
    )
