"""First-law phase-change duties with explicit supplied properties (no property guesses)."""

from .common import positive as p


def phase_change_duty(mass_kg_h, inputs):
    mass = p(mass_kg_h, "phase-changing mass flow kg/h")
    latent = p(
        inputs.get("latent_heat_kj_kg"), "latent heat at specified pressure kJ/kg"
    )
    fraction = p(inputs.get("phase_change_fraction"), "phase-change fraction")
    if fraction > 1:
        raise ValueError("Phase-change fraction cannot exceed one")
    sensible = p(
        inputs.get("sensible_enthalpy_change_kj_kg", 0),
        "sensible enthalpy change",
        zero=True,
    )
    return (
        mass * (latent * fraction + sensible) / 3600,
        "kW",
        {
            "formula": "Q = m_dot * (fraction * latent_heat + sensible_delta_h) / 3600",
            "scope": "Explicit property input must match composition, pressure and phase; no property database was invoked",
        },
    )


def evaporated_water(feed_kg_h, inputs):
    feed = p(feed_kg_h, "wet feed kg/h")
    initial = p(inputs.get("feed_water_mass_fraction"), "feed water mass fraction")
    final = p(
        inputs.get("product_water_mass_fraction"),
        "product water mass fraction",
        zero=True,
    )
    if not 0 <= final < initial < 1:
        raise ValueError(
            "Drying needs 0 <= product moisture < feed moisture < 1 (wet basis)"
        )
    evaporated = feed * (initial - final) / (1 - final)
    return (
        evaporated,
        "kg/h",
        {
            "formula": "m_evap = m_feed * (x_feed - x_product) / (1 - x_product)",
            "scope": "Conserved dry solids; wet-basis moisture; no solids loss or chemical reaction",
        },
    )
