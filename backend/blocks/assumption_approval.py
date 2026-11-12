"""M5.4 per-assumption approval, tied to the exact value, source and version.

Each reviewable assumption (one OPEX line input, the CAPEX settings, the
finance policy) can be approved on its own. An approval stores a SHA-256
fingerprint of the item exactly as saved, the project revision, the reviewer
and the time. If the item changes afterwards, its status becomes
``changed_since_approval``; nothing is approved implicitly.

Approval status is reported, not enforced: unapproved items still calculate,
and every report shows how many are unapproved. Revenue keeps its own
mandatory Revenue Box approval.
"""

import hashlib
import json
from datetime import datetime, timezone

OPEX_GROUPS = ("materials", "energy", "labour", "additional_expenses")


def _fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def reviewable_items(state):
    """{item_key: content} for every reviewable assumption in the saved plan."""
    plan = state.get("plan") or {}
    config = plan.get("operating_economics") or {}
    items = {}
    for group in OPEX_GROUPS:
        for entry in config.get(group) or []:
            if isinstance(entry, dict) and entry.get("id"):
                items[f"opex:{group}:{entry['id']}"] = entry
    if plan.get("capex"):
        items["capex:settings"] = plan["capex"]
    financial = config.get("financial")
    if financial:
        items["finance:policy"] = {k: v for k, v in financial.items() if k != "production_ramp"} | {
            "production_ramp": financial.get("production_ramp")}
    return items


def status(state):
    approvals = state.get("assumption_approvals") or {}
    rows = []
    for key, content in reviewable_items(state).items():
        record = approvals.get(key)
        if not record:
            state_name = "unapproved"
        elif record["fingerprint"] == _fingerprint(content):
            state_name = "approved"
        else:
            state_name = "changed_since_approval"
        rows.append({"item": key, "status": state_name,
                     **({k: record.get(k) for k in ("reviewer", "approved_at", "revision")} if record else {})})
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return {"items": rows, "counts": counts, "all_approved": bool(rows) and counts.get("approved", 0) == len(rows)}


def approve(store, key, revision, item_keys, reviewer, note=""):
    """Approve the named items exactly as currently saved."""
    state = store.get(key)
    if state["revision"] != revision or state.get("running"):
        raise ValueError("Assessment changed or is running; reload before approving")
    if not str(reviewer or "").strip():
        raise ValueError("Name the reviewer")
    items = reviewable_items(state)
    unknown = [k for k in item_keys if k not in items]
    if unknown or not item_keys:
        raise ValueError("Unknown or missing assumption items: " + ", ".join(unknown or ["none given"]))
    store.version(key, "Before assumption approval")
    state = store.get(key)
    approvals = state.setdefault("assumption_approvals", {})
    now = datetime.now(timezone.utc).isoformat()
    for item in item_keys:
        approvals[item] = {"fingerprint": _fingerprint(items[item]), "reviewer": reviewer.strip(),
                           "approved_at": now, "revision": revision, "note": note}
    return store.put(state, state["revision"])
