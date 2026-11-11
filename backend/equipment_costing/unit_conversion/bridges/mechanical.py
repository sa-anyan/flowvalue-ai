"""Mass of a cylindrical shell with supplied thickness and heads/auxiliary mass.
No pressure-code design, thickness prediction or automatic head geometry is implied.
"""

import math
from backend.engineering_sizing.common import positive
from backend.engineering_sizing.versioning import method_metadata


def evaluate(inputs):
    metadata = method_metadata("vessel_mass", evaluate, execution_layer="supplemental")
    d = positive(inputs.get("inside_diameter_m"), "inside diameter m")
    t = positive(inputs.get("wall_thickness_m"), "wall thickness m")
    length = positive(inputs.get("straight_length_m"), "straight shell length m")
    density = positive(inputs.get("material_density_kg_m3"), "material density kg/m3")
    heads = inputs.get("heads_and_auxiliaries_kg")
    if (
        heads is None
        or isinstance(heads, bool)
        or not isinstance(heads, (int, float))
        or not math.isfinite(heads)
        or heads < 0
    ):
        raise ValueError(
            "Supply finite nonnegative heads and auxiliaries mass kg (including explicit zero)"
        )
    return (
        math.pi * ((d / 2 + t) ** 2 - (d / 2) ** 2) * length * density + heads,
        "kg",
        {
            "engineering_method": metadata,
            "formula": "m = pi * ((D/2+t)^2 - (D/2)^2) * L * rho_material + m_heads_aux",
            "scope": "Supplied geometry/thickness only; does not establish code compliance or pressure suitability",
        },
    )
