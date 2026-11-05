"""Recognise simple Excel decimal display masks without changing source numbers.

This is deliberately not a general Excel renderer. Unsupported custom, date,
conditional and locale formats retain their mask but have no display preview.
"""

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from math import isfinite

DECIMAL_MASK = re.compile(r"(?P<group>#,##)?0(?:\.(?P<places>0{1,15}))?(?P<percent>%)?")


def source_display(value, number_format):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not isfinite(value):
        return None
    mask = DECIMAL_MASK.fullmatch(number_format or "")
    if not mask:
        return None
    places = len(mask["places"] or "")
    try:
        with localcontext() as context:
            context.prec = 340
            number = Decimal(str(value)) * (100 if mask["percent"] else 1)
            rounded = number.quantize(
                Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP
            )
            if rounded == 0:
                rounded = abs(rounded)
            return format(rounded, f"{',' if mask['group'] else ''}.{places}f") + (
                "%" if mask["percent"] else ""
            )
    except InvalidOperation:
        return None
