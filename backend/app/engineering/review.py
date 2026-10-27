"""Peer review helpers: revisions are shared explicitly, events remain append-only."""


def open_challenges(events):
    resolved = {e.get("parent_id") for e in events if e.get("action") == "resolve"}
    return [
        e
        for e in events
        if e.get("action") == "challenge" and e.get("id") not in resolved
    ]


def engineering_notes(project):
    from app.engineering.investigation import investigate

    result = []
    for case in (project.study.engineering_cases if project.study else [])[:20]:
        report = investigate(project, case.unit_id)
        result.append(
            f"ENGINEERING INVESTIGATION {case.unit_id}: {report['baseline_status']}; {len(report['blockers'])} unresolved inputs; materials {case.service.wetted_material} / shell {case.service.shell_material}. Preliminary user review, not certification."
        )
    return result


def filter_value(value: str) -> str:
    from urllib.parse import quote

    return quote('"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"', safe="")
