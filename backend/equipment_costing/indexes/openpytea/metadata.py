"""Explicit coordinate vocabulary and cost scopes; original text always retained."""


# Ambiguous gallon/ton units intentionally retain the canonical context requirement.
def coordinate(text):
    s = text.strip().lower().replace("^", "").replace("³", "3").replace("²", "2")
    if s == "weight of shell & two heads, lb":
        return [
            {
                "quantity": "mass",
                "unit": "lb",
                "role": text.strip(),
                "manual_coordinate": False,
            }
        ]
    if s == "m2, filter area":
        return [
            {
                "quantity": "area",
                "unit": "m2",
                "role": text.strip(),
                "manual_coordinate": False,
            }
        ]
    if s == "flow capacity, gpm x sqrt[head, ft]":
        return [
            {
                "quantity": "flow_sqrt_head",
                "unit": "gpm_sqrt_ft",
                "role": text.strip(),
                "manual_coordinate": False,
            }
        ]
    if "&" in s:
        a, b = s.split("&", 1)
        return [coordinate(a)[0], coordinate(b)[0]]
    if s in {
        "(feed, lb/year / 106)0.65",
        "m x mm diameter",
        "s = height x diameter1.5, ft2.5",
        "kg/h/(n/m2)",
        "(lb/hr) / (suction pressure, torr)",
        "flow capacity, gpm x sqrt[head, ft]",
    }:
        return [
            {
                "quantity": "source_coordinate",
                "unit": text.strip(),
                "role": text.strip(),
                "manual_coordinate": True,
            }
        ]
    unit = s.rsplit(",", 1)[-1].strip().rstrip(".")
    if "m2" in unit:
        u, q = "m2", "area"
    elif "ft2" in unit:
        u, q = "ft2", "area"
    elif unit in {"m3", "ft3", "gal"}:
        u, q = unit, "volume"
    elif unit in {
        "m3/h",
        "m3/s",
        "m3/s ",
        "l/s",
        "ft3/hr",
        "gal/min",
        "gpm",
        "acfm",
        "million gal/day",
        "sm3/s",
    }:
        u = {
            "l/s": "L/s",
            "ft3/hr": "ft3/h",
            "gal/min": "gpm",
            "acfm": "cfm",
            "million gal/day": "US_MGD",
            "sm3/s": "Sm3/s",
        }.get(unit, unit)
        q = "standard_volume_flow" if unit == "sm3/s" else "volume_flow"
    elif "ft3/min" in unit:
        u, q = "cfm", "volume_flow"
    elif unit in {
        "kg/h",
        "kg/day",
        "kg/s",
        "lb/hr",
        "lb/s",
        "ton/hr",
        "t/h",
        "metric ton/day",
        "tons crystals/day",
        "tons solids/hr",
    }:
        u = {
            "lb/hr": "lb/h",
            "ton/hr": "ton/h",
            "metric ton/day": "tonne/day",
            "tons crystals/day": "ton/day",
            "tons solids/hr": "ton/h",
        }.get(unit, unit)
        q = "mass_flow"
    elif unit in {"kw", "mwe", "hp", "bhp", "btu/hr", "mmbtu/h"} or "horsepower" in s:
        u = {
            "kw": "kW",
            "mwe": "MW",
            "hp": "hp",
            "bhp": "hp",
            "btu/hr": "Btu_IT/h",
            "mmbtu/h": "million Btu_IT/h",
        }.get(unit, "hp")
        q = "power"
    elif (
        unit in {"m", "mm", "in", "ft"}
        or s == "mm, nominal diameter"
        or "length of the shell, ft" in s
    ):
        u = "mm" if s == "mm, nominal diameter" else unit
        q = "length"
    elif unit in {"kg", "lb"}:
        u, q = unit, "mass"
    else:
        return [
            {
                "quantity": "source_coordinate",
                "unit": text.strip(),
                "role": text.strip(),
                "manual_coordinate": True,
            }
        ]
    return [
        {"quantity": q, "unit": u, "role": text.strip(), "manual_coordinate": False}
    ]


def cost_scope(row):
    text = row.get("Remarks", "").lower().strip()
    if not text:
        return "unresolved"
    installed = "installed" in text or "field assembly" in text
    if "bare-module" in text:
        return "module_estimate"
    if "per tray" in text:
        return "installed_unit_price_per_tray" if installed else "unit_price_per_tray"
    if "us$/ft" in text:
        return "installed_unit_price_per_ft" if installed else "unit_price_per_ft"
    if installed:
        return "installed_equipment"
    if (
        "purchased" in text
        or "purchase" in text
        or "f.o.b" in text
        or "delivered" in text
    ):
        return "purchased_equipment"
    return "unresolved"
