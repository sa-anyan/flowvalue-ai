"""Frozen simulation exports, not a second workbook financial calculator."""

import csv
import io
import json
from itertools import chain

from openpyxl import Workbook


def safe(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def rows(result):
    for run in result["runs"]:
        yield {
            "run": run["index"],
            "status": run["status"],
            **{
                k: run.get("metrics", {}).get(k)
                for k in ("npv", "irr", "payback", "capex", "opex", "known_opex", "revenue")
            },
            "coverage": run.get("coverage", {}).get("fraction"),
            "exceptions": run.get("unpriced", []),
            "errors": run.get("issues", run.get("reason", "")),
            **run.get("samples", {}),
        }


def export(result, kind):
    if kind == "csv":
        output = io.StringIO()
        columns = [
            "run",
            "status",
            "npv",
            "irr",
            "payback",
            "capex",
            "opex",
            "known_opex",
            "revenue",
            "coverage",
            "exceptions",
            "errors",
            *[p["id"] for p in result["settings"]["parameters"] if p["enabled"]],
        ]
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
        writer.writerow({key: safe(key) for key in columns})
        for row in rows(result):
            writer.writerow({k: safe(v) for k, v in row.items()})
        return output.getvalue().encode("utf-8-sig"), "text/csv"
    book = Workbook(write_only=True)

    def sheet(name, data):
        ws = book.create_sheet(name)
        iterator = iter(data)
        first = next(iterator, None)
        if first is None:
            return
        columns = list(first)
        ws.append([safe(key) for key in columns])
        for row in chain([first], iterator):
            ws.append([safe(row.get(k)) for k in columns])

    sheet("Results", rows(result))
    sheet("Parameters", result["settings"]["parameters"])
    sheet("Correlations", result["settings"]["correlations"])
    sheet("Aliases", result["settings"]["aliases"])
    sheet("Distinct assets", result["settings"].get("distinct", []))
    sheet(
        "Percentiles",
        [
            {"metric": key, **{k: v for k, v in value.items() if k != "histogram"}}
            for key, value in result["summary"]["metrics"].items()
        ],
    )
    sheet(
        "Equipment costs",
        (
            {"run": r["index"], "status": r["status"], "tag": tag, "cost": cost}
            for r in result["runs"]
            for tag, cost in r.get("equipment_costs", {}).items()
        ),
    )
    sheet(
        "Cash flows",
        (
            {"run": r["index"], "status": r["status"], **flow}
            for r in result["runs"]
            for flow in r.get("cash_flow", [])
        ),
    )
    for field, name in (
        ("capex_components", "CAPEX components"),
        ("opex_components", "OPEX components"),
        ("equipment_installation_costs", "Equipment installation"),
    ):
        sheet(
            name,
            (
                {
                    "run": r["index"],
                    "status": r["status"],
                    "component": key,
                    "amount": amount,
                }
                for r in result["runs"]
                for key, amount in r.get(field, {}).items()
            ),
        )
    sheet("Unresolved scope", result["audit"]["exceptions"])
    sheet(
        "Exception register",
        [
            {"exception_id": k, **v}
            for k, v in result["audit"].get("exception_register", {}).items()
        ],
    )
    payload = json.dumps(
        {k: v for k, v in result.items() if k != "runs"}, ensure_ascii=False
    )
    sheet(
        "Audit JSON",
        [
            {"chunk": i // 30000, "json": payload[i : i + 30000]}
            for i in range(0, len(payload), 30000)
        ],
    )
    output = io.BytesIO()
    book.save(output)
    return (
        output.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
