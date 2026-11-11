"""Finite engineering-unit catalogue, not an expression evaluator.

SI prefixes and symbols are case-sensitive. Exact length/mass definitions derive
US volume/psi constants. Conventional thermal factors follow NIST SP 811.
"""

import re

from .models import UnitDefinition

INCH = 0.0254
FOOT = 0.3048
POUND = 0.45359237
US_GALLON = 231 * INCH**3
IMP_GALLON = 0.00454609
PSI = POUND * 9.80665 / INCH**2
BTU_IT = 1055.05585262
UNITS = {}
ALIASES = {}
WORDS = {}


def key(unit):
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("Unit must be a nonempty string")
    return re.sub(
        r"\s+",
        " ",
        unit.strip()
        .replace("²", "2")
        .replace("³", "3")
        .replace("^", "")
        .replace("º", "°"),
    )


def add(
    symbol, quantity, factor, aliases=(), words=(), offset=0.0, pressure_basis=None
):
    definition = UnitDefinition(symbol, quantity, factor, offset, pressure_basis)
    UNITS[symbol] = definition
    for alias in (symbol, *aliases):
        k = key(alias)
        if k in ALIASES and ALIASES[k] != symbol:
            raise ValueError("Conflicting alias: " + alias)
        ALIASES[k] = symbol
    for word in words:
        WORDS[key(word).lower()] = symbol


add("item", "count", 1, words=("items", "unit", "units"))
add("tray", "tray_count", 1, words=("trays",))
add("kg", "mass", 1, words=("kilogram", "kilograms"))
add("g", "mass", 0.001, words=("gram", "grams"))
add("mg", "mass", 0.000001, words=("milligram", "milligrams"))
add("lb", "mass", POUND, aliases=("lbs", "lbm"), words=("pound", "pounds"))
add("oz", "mass", POUND / 16, words=("ounce", "ounces"))
add(
    "tonne",
    "mass",
    1000,
    aliases=("metric_ton", "metric tonne"),
    words=("tonne", "tonnes", "metric ton", "metric tons", "metric tonnes"),
)
add(
    "short_ton",
    "mass",
    2000 * POUND,
    words=("short ton", "short tons", "US ton", "US tons"),
)
add("long_ton", "mass", 2240 * POUND, words=("long ton", "long tons", "imperial ton"))
add("m", "length", 1, words=("metre", "metres", "meter", "meters"))
add(
    "cm",
    "length",
    0.01,
    words=("centimeter", "centimeters", "centimetre", "centimetres"),
)
add(
    "mm",
    "length",
    0.001,
    words=("millimeter", "millimeters", "millimetre", "millimetres"),
)
add("in", "length", INCH, words=("inch", "inches"))
add("ft", "length", FOOT, words=("foot", "feet"))
for prefix, factor in [
    ("m", 1),
    ("cm", 0.01),
    ("mm", 0.001),
    ("in", INCH),
    ("ft", FOOT),
]:
    add(prefix + "2", "area", factor**2, aliases=("sq " + prefix,))
    add(prefix + "3", "volume", factor**3, aliases=("cu " + prefix,))
add("L", "volume", 0.001, aliases=("l", "litre", "liter"), words=("litres", "liters"))
add(
    "mL",
    "volume",
    0.000001,
    aliases=("ml",),
    words=("millilitre", "milliliter", "millilitres", "milliliters"),
)
add(
    "US_gal",
    "volume",
    US_GALLON,
    aliases=("US gal", "gal_US"),
    words=("US gallon", "US gallons", "U.S. gallons"),
)
add(
    "Imp_gal",
    "volume",
    IMP_GALLON,
    aliases=("Imperial gal", "gal_Imp"),
    words=("imperial gallon", "imperial gallons", "UK gallon", "UK gallons"),
)
for symbol, factor in [
    ("Pa", 1),
    ("kPa", 1000),
    ("MPa", 1e6),
    ("bar", 1e5),
    ("mbar", 100),
    ("psi", PSI),
    ("atm", 101325),
    ("Torr", 101325 / 760),
    ("mmHg", 133.322387415),
]:
    add(symbol, "pressure", factor)
for symbol, base, basis in [
    ("psig", "psi", "gauge"),
    ("psia", "psi", "absolute"),
    ("barg", "bar", "gauge"),
    ("bara", "bar", "absolute"),
    ("kPag", "kPa", "gauge"),
    ("kPaa", "kPa", "absolute"),
]:
    add(symbol, "pressure", UNITS[base].factor, pressure_basis=basis)
add("K", "temperature", 1, words=("kelvin", "kelvins"))
add(
    "degC",
    "temperature",
    1,
    aliases=("°C", "C"),
    words=("celsius", "degrees Celsius"),
    offset=273.15,
)
add(
    "degF",
    "temperature",
    5 / 9,
    aliases=("°F", "F"),
    words=("fahrenheit", "degrees Fahrenheit"),
    offset=273.15 - 32 * 5 / 9,
)
add("degR", "temperature", 5 / 9, aliases=("°R",), words=("rankine",))
add("delta_K", "temperature_difference", 1)
add("delta_degC", "temperature_difference", 1, aliases=("delta_C", "delta_°C"))
add("delta_degF", "temperature_difference", 5 / 9, aliases=("delta_F", "delta_°F"))
for symbol, factor in [
    ("J", 1),
    ("kJ", 1000),
    ("MJ", 1e6),
    ("GJ", 1e9),
    ("Btu_IT", BTU_IT),
    ("Btu_th", 1054.35026444),
    ("kWh", 3.6e6),
]:
    add(symbol, "energy", factor)
for symbol, factor in [
    ("W", 1),
    ("kW", 1000),
    ("MW", 1e6),
    ("mW", 0.001),
    ("hp", 745.6998715822702),
    ("metric_hp", 735.49875),
    ("refrigeration_ton", 12000 * BTU_IT / 3600),
]:
    add(
        symbol,
        "power",
        factor,
        aliases=("HP",) if symbol == "hp" else (),
        words=(
            (
                "refrigeration ton",
                "refrigeration tons",
                "ton of refrigeration",
                "tons of refrigeration",
            )
            if symbol == "refrigeration_ton"
            else ()
        ),
    )
# Boiler-horsepower identity only: ambiguous source footnote must not silently
# make it mechanical horsepower or a standardized thermal watt rating.
add("boiler_hp", "boiler_power", 1, words=("boiler horsepower",))
add("mol", "amount", 1)
add("kmol", "amount", 1000)
add("kg/m3", "density", 1)
add("g/cm3", "density", 1000)
add("lb/ft3", "density", POUND / FOOT**3)
for numerator in list(UNITS.values()):
    if numerator.quantity not in ["mass", "volume", "energy", "amount"]:
        continue
    dimension = {
        "mass": "mass_flow",
        "volume": "volume_flow",
        "energy": "power",
        "amount": "molar_flow",
    }[numerator.quantity]
    for time, seconds, spellings in [
        ("s", 1, ("sec", "second", "seconds")),
        ("min", 60, ("minute", "minutes")),
        ("h", 3600, ("hr", "hour", "hours")),
        ("day", 86400, ("d", "days")),
    ]:
        add(
            f"{numerator.symbol}/{time}",
            dimension,
            numerator.factor / seconds,
            aliases=tuple(f"{numerator.symbol}/{x}" for x in spellings),
        )
add("cfm", "volume_flow", FOOT**3 / 60, aliases=())
add("US_gpm", "volume_flow", US_GALLON / 60, aliases=("US gal/min",))
add("Imp_gpm", "volume_flow", IMP_GALLON / 60, aliases=("Imperial gal/min",))
add("scfm", "standard_volume_flow", FOOT**3 / 60)
add("Nm3/h", "standard_volume_flow", 1 / 3600, aliases=("Nm³/h",))
add("Sm3/h", "standard_volume_flow", 1 / 3600, aliases=("Sm³/h",))
add("US_gpm_psi", "flow_pressure_product", US_GALLON / 60 * PSI)
add("Imp_gpm_psi", "flow_pressure_product", IMP_GALLON / 60 * PSI)
add("m3/s_Pa", "flow_pressure_product", 1, aliases=("m3/s*Pa",))
add("kg/h/mmHg_abs", "vacuum_capacity", 1 / 3600 / 133.322387415)
add("lb/h/mmHg_abs", "vacuum_capacity", POUND / 3600 / 133.322387415)

ALIASES["ft_height"] = "ft"

# Canonical ingestion pressure labels retain their gauge/absolute basis across
# the parser -> conversion -> costing boundary. These are aliases, not new units.
for _label, _symbol in {
    "bar_gauge": "barg",
    "bar_abs": "bara",
    "bar_absolute": "bara",
    "psi_gauge": "psig",
    "psi_abs": "psia",
    "psi_absolute": "psia",
}.items():
    ALIASES[key(_label)] = _symbol

# Explicit US million gallons/day; ambiguous MGD is deliberately not an alias.
add("US_MGD", "volume_flow", 1e6 * US_GALLON / 86400, aliases=("US MGD", "MGD_US"))

add("Sm3/s", "standard_volume_flow", 1)

add("US_gpm_sqrt_ft", "flow_sqrt_head", US_GALLON / 60 * FOOT**0.5)
add("Imp_gpm_sqrt_ft", "flow_sqrt_head", IMP_GALLON / 60 * FOOT**0.5)
add("m3/h_sqrt_m", "flow_sqrt_head", 1 / 3600)

# Active native-parameter interfaces (UNIT-003). These are finite units, not
# permission to evaluate arbitrary compound expressions. Hydraulic loading is
# a velocity, never a volumetric flow. Heat-transfer coefficients use intervals.
add("m/s", "velocity", 1)
add("m/h", "velocity", 1 / 3600, aliases=("m3/m2/h",))
add("ft/s", "velocity", FOOT)
add("ft/min", "velocity", FOOT / 60)
for symbol, seconds, spellings in [
    ("s", 1, ("sec", "second", "seconds")),
    ("min", 60, ("minute", "minutes")),
    ("h", 3600, ("hr", "hour", "hours")),
    ("day", 86400, ("d", "days")),
]:
    add(symbol, "time", seconds, words=spellings)
add(
    "W/m2/K",
    "heat_transfer_coefficient",
    1,
    aliases=("W/(m2 K)", "W/(m2*K)", "W/(m2*delta_K)"),
)
add(
    "kW/m2/K",
    "heat_transfer_coefficient",
    1000,
    aliases=("kW/(m2 K)", "kW/(m2*K)"),
)
for symbol, energy in [("Btu_IT", BTU_IT), ("Btu_th", 1054.35026444)]:
    add(
        symbol + "/(h*ft2*delta_degF)",
        "heat_transfer_coefficient",
        energy / (3600 * FOOT**2 * (5 / 9)),
        aliases=(symbol + "/(h ft2 °F)", symbol + "/(h*ft2*°F)"),
    )
