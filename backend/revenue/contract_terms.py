"""M4.3 contract terms: payments stay inside supported contract dates.

Roadmap Phase 4 acceptance: "Contracts do not extend beyond their supported
dates without an explicit assumption."

A saved commercial line may carry::

    "contract_term": {
        "start_year": 2026,           # first calendar year paid (optional)
        "end_year": 2027,             # last calendar year paid (null = open-ended)
        "basis": "Signed heads of terms, clause 4",
        "renewals": [
            {"start_year": 2028, "end_year": 2035, "status": "assumed",
             "basis": "Renewal on the same terms is a planning assumption"},
        ],
    }

Operating year n falls in calendar year
``calendar_start_year + construction_years + n - 1``, the same mapping the
financial model uses. A year outside the term and every renewal must have no
payment (rate, fixed payment and minimum payment all zero); otherwise the
line is rejected. Lines without a contract term keep the existing behaviour:
each listed year is an explicit annual assumption.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

RENEWAL_STATUSES = {"assumed", "confirmed"}


def first_operating_calendar_year(config):
    financial = config.get("financial") or {}
    start = financial.get("calendar_start_year")
    if start is None:
        start = date.fromisoformat(config["assumption_date"]).year
    return int(start) + int(financial.get("construction_years", 0))


def _year(value, label, name):
    if value is None:
        return None
    if type(value) is not int:
        raise ValueError(f"Contract term for {name}: {label} must be a calendar year")
    return value


def _periods(term, name):
    if not isinstance(term, dict):
        raise ValueError(f"Contract term for {name} must be an object")
    if not str(term.get("basis") or "").strip():
        raise ValueError(f"Contract term for {name} needs a basis (where the dates come from)")
    periods = [(_year(term.get("start_year"), "start_year", name),
                _year(term.get("end_year"), "end_year", name), "contract")]
    for renewal in term.get("renewals") or []:
        status = renewal.get("status")
        if status not in RENEWAL_STATUSES:
            raise ValueError(f"Renewal for {name} needs status assumed or confirmed")
        if not str(renewal.get("basis") or "").strip():
            raise ValueError(f"Renewal for {name} needs a basis")
        start = _year(renewal.get("start_year"), "renewal start_year", name)
        if start is None:
            raise ValueError(f"Renewal for {name} needs a start_year")
        periods.append((start, _year(renewal.get("end_year"), "renewal end_year", name),
                        "renewal_" + status))
    for start, end, _ in periods:
        if start is not None and end is not None and end < start:
            raise ValueError(f"Contract term for {name} ends before it starts")
    return periods


def _pays(row):
    for key in ("rate", "fixed_payment", "minimum_payment"):
        value = row.get(key)
        if value is None:
            continue
        try:
            if Decimal(str(value)) != 0:
                return True
        except (InvalidOperation, ValueError):
            return True
    return False


def coverage(item, config):
    """Return {operating_year: basis} for a line, or None if it has no term.

    Raises ValueError when a paying year is outside the term and renewals.
    """
    term = item.get("contract_term")
    if not term:
        return None
    name = item.get("name") or item.get("id") or "commercial line"
    periods = _periods(term, name)
    first = first_operating_calendar_year(config)
    result = {}
    for row in item.get("years", []):
        calendar = first + int(row["year"]) - 1
        basis = next(
            (kind for start, end, kind in periods
             if (start is None or calendar >= start) and (end is None or calendar <= end)),
            None,
        )
        if basis is None and _pays(row):
            raise ValueError(
                f"{name} pays in {calendar} (operating year {row['year']}), outside its contract "
                "term and renewals; add a renewal with its basis, or set that year's payments to zero"
            )
        result[int(row["year"])] = {"calendar_year": calendar, "basis": basis or "outside_term_no_payment"}
    return result


def describe(item, config):
    """Short text for the line's rationale, or "" if it has no term."""
    years = coverage(item, config)
    if not years:
        return ""
    renewals = sorted({v["calendar_year"] for v in years.values() if v["basis"].startswith("renewal_")})
    assumed = any(v["basis"] == "renewal_assumed" for v in years.values())
    text = f"contract term {item['contract_term'].get('start_year') or 'open'}–{item['contract_term'].get('end_year') or 'open'}"
    if renewals:
        text += f"; renewal years {renewals[0]}–{renewals[-1]}" + (" (assumed)" if assumed else " (confirmed)")
    return text
