"""Only extract/review engineering data. Never size or price equipment."""

from backend.orchestration.ingest import parse
from backend.orchestration.codec import plain
from backend.blocks.models import Product, DataRequired


def calculate(ctx):
    if not ctx.content:
        raise DataRequired("Data required: upload a mass and energy balance workbook.")
    parsed = parse(ctx.content, ctx.state["filename"])
    report = parsed["report"]
    updates = {
        "parsed": parsed,
        "effective_report": report,
        "source_sha256": report["sha256"],
    }
    notes = []
    if ctx.use_ai:
        from backend.orchestration.workbook_review import review

        try:
            from backend.orchestration.provider import EngineeringProvider

            provider = ctx.provider or EngineeringProvider()
            effective, interpretation, decisions, meta = review(
                parsed, ctx.state.get("description", ""), ctx.store, provider
            )
            report = effective
            updates.update(
                effective_report=effective,
                engineering_review=interpretation,
                recoveries=decisions,
                ai={"review": meta},
            )
        except Exception as exc:
            from backend.revenue.advisor import safe_ai_reason

            notes.append(
                "AI review unavailable ("
                + safe_ai_reason(exc)
                + "); Python extraction retained for inspection."
            )
            updates["ai"] = {"status": "review_unavailable", "notice": notes[-1]}
    from .edits import apply_edit

    for edit in ctx.state.get("engineering_register_edits", []):
        if edit.get("action") == "remove" and not any(
            e["key"] == edit["equipment_key"] for e in report["entities"]
        ):
            continue
        report, _ = apply_edit(report, edit)
    updates["effective_report"] = report
    result = {
        "status": "parsed",
        "filename": report["filename"],
        "sheets": report["sheets"],
        "equipment_count": sum(e["kind"] == "equipment" for e in report["entities"]),
        "material_stream_count": sum(
            e["kind"] == "material" for e in report["entities"]
        ),
        "energy_stream_count": sum(e["kind"] == "energy" for e in report["entities"]),
        "issues": report.get("issues", []),
        "review_notices": notes,
    }
    return Product(
        result,
        {
            "report": report,
            "source_cells": parsed.get("source_cells", []),
            "source_cells_truncated": parsed.get("source_cells_truncated", False),
        },
        updates,
    )
