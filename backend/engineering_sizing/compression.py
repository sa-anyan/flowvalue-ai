"""Single-stage ideal-gas isentropic compression screening, explicit applicability."""

from .common import positive as p


def calculate(mass_kg_h, inputs):
    mass = p(mass_kg_h, "gas mass kg/h") / 3600
    mw = p(inputs.get("molecular_weight_kg_kmol"), "mixture MW kg/kmol")
    temp = p(inputs.get("temperature_k"), "inlet gas K")
    pin = p(inputs.get("absolute_pressure_bar"), "inlet absolute pressure bar")
    pout = p(inputs.get("discharge_pressure_bar"), "outlet absolute pressure bar")
    ratio = pout / pin
    k = p(inputs.get("heat_capacity_ratio"), "heat capacity ratio")
    eta = p(inputs.get("efficiency"), "isentropic efficiency")
    z = p(inputs.get("compressibility_z"), "compressibility Z")
    if k <= 1 or k > 2 or eta > 1 or ratio <= 1:
        raise ValueError(
            "Compression requires 1 < k <= 2, efficiency <=1 and outlet > inlet pressure"
        )
    power = (
        mass
        * (8.31446261815324 / mw)
        * temp
        * z
        * k
        / (k - 1)
        * (ratio ** ((k - 1) / k) - 1)
        / eta
    )
    return (
        power,
        "kW",
        {
            "formula": "W = m R T Z k/(k-1) * ((Pout/Pin)^((k-1)/k)-1) / eta",
            "scope": "Single-stage gas screening only; constant k and Z, no condensation/intercooling; applicability must be reviewed",
        },
    )
