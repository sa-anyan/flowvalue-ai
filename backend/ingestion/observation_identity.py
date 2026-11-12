"""Identity metadata for existing evidence records outside workbook extraction."""

import re

from backend.ingestion.engineering_register import stable_key

RECOVERY_PREFIXES = ("recovery:", "ai-evidence:")


def recovered_identity(source_sha256, evidence_id, method=None):
    if not isinstance(source_sha256, str) or not re.fullmatch("[0-9a-f]{64}", source_sha256):
        return {"observation_identity_limitation": "missing_source_content_identity"}
    return {
        "observation_id": stable_key("observation", source_sha256, evidence_id),
        "observation_method": method,
    }


def project_report_evidence(report):
    """Annotate historical records in a response copy only."""
    evidence = list(report.get("declarations", []))
    for entity in report.get("entities", []):
        evidence.extend([entity.get("id_evidence") or {}, *entity.get("values", [])])
    for value in evidence:
        if not value or value.get("observation_id"):
            continue
        key = value.get("id")
        if isinstance(key, str) and key.startswith(RECOVERY_PREFIXES):
            value.update(recovered_identity(report.get("sha256"), key))
        else:
            value["observation_identity_limitation"] = "historical_observation_identity_unavailable"
