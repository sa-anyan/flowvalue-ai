"""M4.6 reconciled financial workbook, written from one saved study.

Reads the saved revenue, OPEX and financial stage results. No engine, web or
AI call runs. The only arithmetic is the reconciliation checks, done in
Decimal and written to their own sheet:

- ledger revenue in each operating period equals the revenue stage's annual
  revenue;
- each year's annual revenue equals product sales plus commercial payments;
- ledger fixed plus variable OPEX equals the OPEX stage's annual cash OPEX;
- project NPV equals the sum of discounted project cash;
- every number written to the workbook equals its saved value (checked by
  reading the workbook back).

Cells hold numbers for use in a spreadsheet; the exact saved values are kept
as text in the JSON snapshot download.
"""

import json
from decimal import Decimal, InvalidOperation
from io import BytesIO

VERSION = "financial-workbook-2"
TOLERANCE = Decimal("1e-9")  # relative, per check

CASH_FLOW_ROWS = (
    "revenue", "variable_opex", "fixed_opex", "cogs", "gross_profit", "ebitda",
    "depreciation", "ebit", "interest", "profit_before_tax", "income_tax", "net_income",
    "capex", "startup_expense", "working_capital_change", "working_capital_recovery",
    "disposal_proceeds", "closure_expense", "operating_cash_flow", "investing_cash_flow",
    "financing_cash_flow", "fcff", "fcfe", "cfads", "cumulative_project_cash",
    "discounted_project_cash", "cumulative_equity_cash", "discounted_equity_cash",
)


def _dec(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return number if number.is_finite() else None


def _close(a, b):
    if a is None or b is None:
        return False
    return abs(a - b) <= TOLERANCE * max(Decimal(1), abs(a), abs(b))


def _result(state, stage):
    return (((state.get("results") or {}).get("stages") or {}).get(stage) or {}).get("result") or {}


def _construction_years(state):
    config = ((state.get("plan") or {}).get("operating_economics") or {}).get("financial") or {}
    return int(config.get("construction_years", 0))


def reconcile(state):
    """Decimal checks between the saved stages. Returns a list of check dicts."""
    financial = _result(state, "financial")
    revenue = _result(state, "revenue")
    opex = (_result(state, "opex").get("years") or {})
    build = _construction_years(state)
    ledger = {int(l["period"]["year"]): l for l in financial.get("ledger") or []}
    checks = []

    def add(check, year, left, right, left_label, right_label):
        checks.append({
            "check": check, "year": year,
            "left_label": left_label, "left": str(left) if left is not None else None,
            "right_label": right_label, "right": str(right) if right is not None else None,
            "difference": str(left - right) if left is not None and right is not None else None,
            "passed": _close(left, right),
        })

    for annual in revenue.get("annual") or []:
        year = int(annual["year"])
        row = ledger.get(year + build) or {}
        add("Ledger revenue = revenue stage", year, _dec(row.get("revenue")), _dec(annual["sales_revenue"]),
            "financial ledger", "revenue stage")
        parts = sum((_dec(p["net_sales_revenue"]) or Decimal(0) for p in revenue.get("products") or [] if int(p["year"]) == year), Decimal(0))
        parts += sum((_dec(c["revenue"]) or Decimal(0) for c in revenue.get("commercial") or [] if int(c["year"]) == year), Decimal(0))
        add("Revenue = products + commercial payments", year, _dec(annual["sales_revenue"]), parts,
            "annual revenue", "sum of sources")
    for key, values in sorted(opex.items(), key=lambda kv: int(kv[0])):
        year = int(key)
        row = ledger.get(year + build) or {}
        fixed, variable = _dec(row.get("fixed_opex")), _dec(row.get("variable_opex"))
        add("Ledger OPEX = OPEX stage cash OPEX", year,
            (fixed + variable) if fixed is not None and variable is not None else None,
            _dec(values.get("annual_cash_opex")), "ledger fixed + variable", "OPEX stage")
    metrics = dict(financial.get("metrics") or [])
    npv = _dec((metrics.get("project_npv") or {}).get("value"))
    discounted = [_dec(l.get("discounted_project_cash")) for l in ledger.values()]
    total = sum(discounted, Decimal(0)) if all(d is not None for d in discounted) else None
    add("Project NPV = sum of discounted project cash", None, npv, total, "NPV metric", "ledger sum")
    return checks


def build_financial_workbook(state):
    """Return (xlsx bytes, summary). Raises ValueError if finance has not run."""
    import openpyxl
    from openpyxl.styles import Font

    financial = _result(state, "financial")
    if not financial.get("ledger"):
        raise ValueError("Run the financial stage first; the workbook is written only from a saved result.")
    revenue, opex = _result(state, "revenue"), _result(state, "opex")
    build = _construction_years(state)
    checks = reconcile(state)
    bold = Font(bold=True)
    book = openpyxl.Workbook()
    written = []  # (sheet, cell, Decimal) for the read-back check

    def put(sheet, row, column, value):
        number = None if isinstance(value, bool) or value is None else _dec(value)
        cell = sheet.cell(row=row, column=column)
        if number is not None:
            cell.value = float(number)
            written.append((sheet.title, cell.coordinate, number))
        else:
            cell.value = value
        return cell

    # Summary
    summary = book.active
    summary.title = "Summary"
    rows = [
        ("FlowValue financial workbook", VERSION),
        ("Assessment", state.get("id")), ("Revision", state.get("revision")),
        ("Source file", state.get("filename")), ("Source SHA-256", state.get("source_sha256")),
        ("Currency", financial.get("currency")), ("Price mode", financial.get("price_mode")),
        ("Financial base year", financial.get("financial_base_year")),
        ("Discount convention", financial.get("discount_convention")),
        ("Status", financial.get("status")),
        ("Reconciliation", "all checks pass" if all(c["passed"] for c in checks) else "CHECK FAILED; see Reconciliation"),
        ("Assumption approvals", _approval_summary(state)),
        ("Notice", "Written from the saved study; no figure is recalculated except the reconciliation checks."),
    ]
    for i, (k, v) in enumerate(rows, 1):
        summary.cell(row=i, column=1, value=k).font = bold
        summary.cell(row=i, column=2, value=str(v) if v is not None else "")
    start = len(rows) + 2
    for j, head in enumerate(("Metric", "Value", "Unit", "Status", "Basis"), 1):
        summary.cell(row=start, column=j, value=head).font = bold
    for i, (name, metric) in enumerate(financial.get("metrics") or [], start + 1):
        summary.cell(row=i, column=1, value=name)
        put(summary, i, 2, metric.get("value"))
        summary.cell(row=i, column=3, value=metric.get("unit"))
        summary.cell(row=i, column=4, value=metric.get("status"))
        summary.cell(row=i, column=5, value=metric.get("basis"))

    # Cash flow: one column per ledger period
    cash = book.create_sheet("Cash flow")
    ledger = sorted(financial["ledger"], key=lambda l: int(l["period"]["year"]))
    cash.cell(row=1, column=1, value="Project year").font = bold
    cash.cell(row=2, column=1, value="Calendar year").font = bold
    cash.cell(row=3, column=1, value="Operating year").font = bold
    for j, l in enumerate(ledger, 2):
        year = int(l["period"]["year"])
        cash.cell(row=1, column=j, value=year)
        cash.cell(row=2, column=j, value=l["period"].get("calendar_year"))
        cash.cell(row=3, column=j, value=(year - build) if year - build >= 1 else None)
    for i, field in enumerate(CASH_FLOW_ROWS, 4):
        cash.cell(row=i, column=1, value=field.replace("_", " ").capitalize())
        for j, l in enumerate(ledger, 2):
            put(cash, i, j, l.get(field))

    # Revenue by source and year
    rev = book.create_sheet("Revenue")
    years = sorted({int(a["year"]) for a in revenue.get("annual") or []})
    rev.cell(row=1, column=1, value="Source").font = bold
    rev.cell(row=1, column=2, value="Category").font = bold
    for j, y in enumerate(years, 3):
        rev.cell(row=1, column=j, value=f"Operating year {y}").font = bold
    sources = {}
    for p in revenue.get("products") or []:
        sources.setdefault(("product:" + p["product_id"], "product_sales"), {})[int(p["year"])] = p["net_sales_revenue"]
    for c in revenue.get("commercial") or []:
        sources.setdefault((c["payment_id"], c["category"]), {})[int(c["year"])] = c["revenue"]
    row = 2
    for (name, category), by_year in sources.items():
        rev.cell(row=row, column=1, value=name)
        rev.cell(row=row, column=2, value=category)
        for j, y in enumerate(years, 3):
            put(rev, row, j, by_year.get(y))
        row += 1
    rev.cell(row=row, column=1, value="Total revenue").font = bold
    annual = {int(a["year"]): a["sales_revenue"] for a in revenue.get("annual") or []}
    for j, y in enumerate(years, 3):
        put(rev, row, j, annual.get(y))
    saved = revenue.get("avoided_costs") or []
    if saved:
        row += 2
        rev.cell(row=row, column=1, value="Avoided costs (reduce OPEX; not revenue)").font = bold
        for s in saved:
            row += 1
            rev.cell(row=row, column=1, value=s.get("id"))
            rev.cell(row=row, column=2, value="reduces " + str(s.get("target_opex_id")))

    # OPEX by year
    op = book.create_sheet("OPEX")
    for j, head in enumerate(("Operating year", "Fixed cash OPEX", "Variable cash OPEX", "Annual cash OPEX"), 1):
        op.cell(row=1, column=j, value=head).font = bold
    for i, (key, values) in enumerate(sorted((opex.get("years") or {}).items(), key=lambda kv: int(kv[0])), 2):
        op.cell(row=i, column=1, value=int(key))
        put(op, i, 2, values.get("cash_fixed"))
        put(op, i, 3, values.get("cash_variable"))
        put(op, i, 4, values.get("annual_cash_opex"))

    # OPEX lines (first operating year): who pays, escalation basis, source
    lines_sheet = book.create_sheet("OPEX lines")
    first = sorted((opex.get("years") or {}), key=int)[:1]
    heads = ("Line", "Category", "Behaviour", "Quantity", "Quantity unit", "Rate", "Rate unit",
             "Amount", "Payment owner", "Escalation basis", "Source")
    for j, head in enumerate(heads, 1):
        lines_sheet.cell(row=1, column=j, value=head).font = bold
    row = 2
    if first:
        year = first[0]
        lines_sheet.cell(row=row, column=1, value=f"Operating year {year}").font = bold
        row += 1
        for line in (opex["years"][year].get("lines") or []):
            evidence = [str(e) for e in line.get("evidence") or []]
            tag = lambda prefix: next((e[len(prefix):] for e in evidence if e.startswith(prefix)), "")  # noqa: E731
            values = (line.get("id"), line.get("category"), line.get("behavior"), line.get("quantity"),
                      line.get("quantity_unit"), line.get("rate"), line.get("rate_unit"), line.get("amount"),
                      tag("payment owner: ") or "project (not recorded)", tag("escalation basis: "), line.get("source"))
            for j, value in enumerate(values, 1):
                if j in (4, 6, 8):
                    put(lines_sheet, row, j, value)
                else:
                    lines_sheet.cell(row=row, column=j, value=value)
            row += 1
        detail = ((opex.get("operating_detail") or {}).get("years") or {}).get(year) or {}
        others = detail.get("paid_by_others") or []
        if others:
            row += 1
            lines_sheet.cell(row=row, column=1, value="Paid by others (not in project OPEX)").font = bold
            for other in others:
                row += 1
                values = (other.get("id"), other.get("category"), "", other.get("quantity"), "", other.get("rate"),
                          "", other.get("amount"), other.get("payment_owner"), other.get("escalation_basis"),
                          other.get("basis"))
                for j, value in enumerate(values, 1):
                    if j in (4, 6, 8):
                        put(lines_sheet, row, j, value)
                    else:
                        lines_sheet.cell(row=row, column=j, value=value)

    # Reconciliation
    rec = book.create_sheet("Reconciliation")
    heads = ("Check", "Operating year", "Left", "Left value", "Right", "Right value", "Difference", "Result")
    for j, head in enumerate(heads, 1):
        rec.cell(row=1, column=j, value=head).font = bold
    for i, c in enumerate(checks, 2):
        rec.cell(row=i, column=1, value=c["check"])
        rec.cell(row=i, column=2, value=c["year"])
        rec.cell(row=i, column=3, value=c["left_label"])
        put(rec, i, 4, c["left"])
        rec.cell(row=i, column=5, value=c["right_label"])
        put(rec, i, 6, c["right"])
        put(rec, i, 7, c["difference"])
        rec.cell(row=i, column=8, value="pass" if c["passed"] else "FAIL")
    rec.cell(row=len(checks) + 3, column=1,
             value=f"Tolerance: relative {TOLERANCE} on Decimal values from the saved study.")

    # Assumptions and sources
    assumptions = book.create_sheet("Assumptions")
    try:
        parsed = json.loads(financial.get("assumptions_json") or "{}")
        text = json.dumps(parsed, indent=1, sort_keys=True, default=str)
    except (ValueError, TypeError):
        text = str(financial.get("assumptions_json"))
    for i, line in enumerate(text.splitlines()[:5000], 1):
        assumptions.cell(row=i, column=1, value=line[:32000])
    src = book.create_sheet("Sources")
    for i, s in enumerate(financial.get("sources") or [], 1):
        src.cell(row=i, column=1, value=str(s)[:32000])

    data = BytesIO()
    book.save(data)
    content = data.getvalue()
    # Read back: every number in the file must equal its saved value.
    reread = openpyxl.load_workbook(BytesIO(content), data_only=True)
    mismatched = [
        f"{sheet}!{cell}" for sheet, cell, expected in written
        if not _close(_dec(reread[sheet][cell].value), expected)
    ]
    summary_out = {
        "version": VERSION,
        "checks": len(checks),
        "checks_failed": [c for c in checks if not c["passed"]],
        "numbers_written": len(written),
        "readback_mismatches": mismatched,
        "reconciled": all(c["passed"] for c in checks) and not mismatched,
    }
    return content, summary_out



def _approval_summary(state):
    from backend.blocks.assumption_approval import status

    counts = status(state)["counts"]
    return ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in sorted(counts.items())) or "no reviewable assumptions"
