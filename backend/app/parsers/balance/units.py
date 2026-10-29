"""Explicit dimensional conversion registry. Ambiguous bases stay unresolved."""

import math
import re
import unicodedata
from functools import lru_cache


def clean(value):
    return re.sub(
        r"\s+",
        " ",
        unicodedata.normalize("NFKC", str(value or "")).replace("−", "-").strip(),
    ).lower()


def unit_key(value):
    u = (
        clean(value)
        .replace("°", "")
        .replace("³", "3")
        .replace("^", "")
        .replace(" ", "")
        .replace("·", "")
        .replace("per", "/")
        .replace("hr", "h")
        .replace("sec", "s")
    )
    u = (
        u.replace("hour", "h")
        .replace("kelvin", "k")
        .replace("celsius", "c")
        .replace("fahrenheit", "f")
    )
    # Preserve explicit absolute/gauge qualifiers; these are not wrapper brackets.
    if u in {"bar(a)", "bar(g)", "pa(a)", "kpa(a)"}:
        return u
    return u.strip("[]()")


# canonical unit, factor, offset. Absolute/gauge pressure is deliberately distinct.
UNITS = {
    "mass_flow": {
        "kg/h": ("kg/h", 1, 0),
        "kg/s": ("kg/h", 3600, 0),
        "kg/min": ("kg/h", 60, 0),
        "g/s": ("kg/h", 3.6, 0),
        "g/h": ("kg/h", 0.001, 0),
        "t/h": ("kg/h", 1000, 0),
        "tonne/h": ("kg/h", 1000, 0),
        "lb/h": ("kg/h", 0.45359237, 0),
        "lb/s": ("kg/h", 1632.932532, 0),
    },
    "molar_flow": {
        "kmol/h": ("kmol/h", 1, 0),
        "kmol/s": ("kmol/h", 3600, 0),
        "mol/s": ("kmol/h", 3.6, 0),
        "mol/h": ("kmol/h", 0.001, 0),
        "lbmol/h": ("kmol/h", 0.45359237, 0),
    },
    "temperature": {
        "c": ("degC", 1, 0),
        "degc": ("degC", 1, 0),
        "k": ("degC", 1, -273.15),
        "f": ("degC", 5 / 9, -32 * 5 / 9),
        "degf": ("degC", 5 / 9, -32 * 5 / 9),
    },
    "pressure": {
        "bara": ("bar_abs", 1, 0),
        "barabs": ("bar_abs", 1, 0),
        "bar(a)": ("bar_abs", 1, 0),
        "bar_abs": ("bar_abs", 1, 0),
        "pa(a)": ("bar_abs", 1e-5, 0),
        "paa": ("bar_abs", 1e-5, 0),
        "pag": ("bar_gauge", 1e-5, 0),
        "kpag": ("bar_gauge", 0.01, 0),
        "mpag": ("bar_gauge", 10, 0),
        "kpa(a)": ("bar_abs", 0.01, 0),
        "kpaa": ("bar_abs", 0.01, 0),
        "mpaa": ("bar_abs", 10, 0),
        "psia": ("bar_abs", 0.0689475729, 0),
        "atm": ("bar_abs", 1.01325, 0),
        "barg": ("bar_gauge", 1, 0),
        "bar(g)": ("bar_gauge", 1, 0),
        "psig": ("bar_gauge", 0.0689475729, 0),
    },
    "density": {
        "kg/m3": ("kg/m3", 1, 0),
        "g/cm3": ("kg/m3", 1000, 0),
        "lb/ft3": ("kg/m3", 16.01846337, 0),
    },
    "power": {
        "w": ("kW", 0.001, 0),
        "kw": ("kW", 1, 0),
        "mw": ("kW", 1000, 0),
        "kj/h": ("kW", 1 / 3600, 0),
        "kj/s": ("kW", 1, 0),
        "btu/h": ("kW", 0.00029307107, 0),
        "kcal/h": ("kW", 0.00116222222, 0),
        "hp": ("kW", 0.745699872, 0),
    },
    "enthalpy": {
        "j/kg": ("kJ/kg", 0.001, 0),
        "kj/kg": ("kJ/kg", 1, 0),
        "btu/lb": ("kJ/kg", 2.326, 0),
        "kj/kmol": ("kJ/kmol", 1, 0),
    },
    "fraction": {
        "%": ("fraction", 0.01, 0),
        "wt%": ("fraction", 0.01, 0),
        "mol%": ("fraction", 0.01, 0),
        "massfraction": ("fraction", 1, 0),
        "molefraction": ("fraction", 1, 0),
        "fraction": ("fraction", 1, 0),
    },
    "volume_flow": {
        "m3/h": ("m3/h", 1, 0),
        "m3/s": ("m3/h", 3600, 0),
        "l/min": ("m3/h", 0.06, 0),
    },
    "volume": {"m3": ("m3", 1, 0), "l": ("m3", 0.001, 0)},
    "length": {"m": ("m", 1, 0), "mm": ("m", 0.001, 0), "ft": ("m", 0.3048, 0)},
    "area": {"m2": ("m2", 1, 0), "ft2": ("m2", 0.09290304, 0)},
    "concentration": {
        "kg/m3": ("kg/m3", 1, 0),
        "g/l": ("kg/m3", 1, 0),
        "mg/l": ("kg/m3", 0.001, 0),
    },
}
UNIT_TOKENS = sorted(
    {k for d in UNITS.values() for k in d}
    | {"bar", "pa", "kpa", "mpa", "%", "kg/hour"},
    key=len,
    reverse=True,
)


UNIT_PATTERNS = [(token, re.compile(r"(?<![a-z])" + re.escape(token) + r"(?![a-z0-9])")) for token in UNIT_TOKENS]


def find_unit(label):
    return _find_unit(clean(label))


@lru_cache(maxsize=4096)
def _find_unit(text):
    bracket = re.findall(r"\[([^\]]+)\]|\(([^)]+)\)", text)
    for a, b in reversed(bracket):
        u = a or b
        if unit_key(u) in UNIT_TOKENS:
            return u
    # retain pressure bases: bar(a) must be matched before bare bar
    search_text = text.replace(" ", "").replace("°", "")
    for token, pattern in UNIT_PATTERNS:
        if pattern.search(search_text):
            return token
    return (bracket[-1][0] or bracket[-1][1]) if bracket else None


def number(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (float, int)):
        return float(value) if math.isfinite(value) else None
    s = str(value).strip().replace("−", "-")
    # Ambiguous comma decimal/thousands are not guessed.
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eEdD][+-]?\d+)?", s):
        return None
    try:
        n = float(s.lower().replace("d", "e"))
        return n if math.isfinite(n) else None
    except ValueError:
        return None


def convert(value, dimension, unit):
    n = number(value)
    if n is None:
        return (
            None,
            None,
            "Missing, non-finite or ambiguous numeric value; no substitution made.",
        )
    entry = UNITS.get(dimension, {}).get(unit_key(unit))
    if not entry:
        return (
            None,
            None,
            "Missing, unsupported or dimensionally inconsistent unit. Pressure requires an explicit absolute/gauge basis.",
        )
    target, factor, offset = entry
    result = n * factor + offset
    if not math.isfinite(result):
        return None, None, "Conversion overflow."
    if (
        (
            dimension
            in (
                "mass_flow",
                "molar_flow",
                "density",
                "volume_flow",
                "volume",
                "length",
                "area",
                "concentration",
            )
            and result < 0
        )
        or (dimension == "temperature" and result < -273.15)
        or (dimension == "pressure" and target == "bar_abs" and result <= 0)
        or (dimension == "fraction" and not 0 <= result <= 1)
    ):
        return (
            None,
            target,
            "Physically invalid value for the declared property; retained without correction.",
        )
    return result, target, ""
