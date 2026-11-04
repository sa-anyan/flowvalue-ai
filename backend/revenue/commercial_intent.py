"""User-stated payment mechanisms govern initial revenue routing.

This verifies source quotes and category coverage; semantic interpretation is an LLM
proposal, not proof of a contract. Unknown intent must never become product sales.
"""

from .advisor import TEXT, obj
from .validation import CATEGORIES

SCHEMA = obj(
    {
        "status": {"type": "string", "enum": ["explicit", "needs_clarification"]},
        "mechanisms": {
            "type": "array",
            "items": obj(
                {
                    "id": TEXT,
                    "category": {"type": "string", "enum": list(CATEGORIES)},
                    "context_quote": TEXT,
                    "interpretation": TEXT,
                }
            ),
        },
        "questions": {"type": "array", "items": TEXT},
    }
)
PROMPT = """COMMERCIAL INTENT IS THE SOURCE OF TRUTH. First read how the USER expects
this project to earn money; fill commercial_intent with one or several distinct payment
mechanisms and exact supporting quotations. Equipment names and physical outputs DO NOT
establish income. Clean water produced is NOT evidence that it is sold. Being paid to
treat water is processing_services, not water/product sales. Capacity, access, credits and
other contractual payments are independent categories. If only service fees are stated,
sales must be empty and no by-product sales may be invented. If several mechanisms are
stated, cover ALL of them, each once, with a distinct mechanism id. Every sales or
commercial_lines entry must carry intent_id referencing its actual user-stated mechanism.
Only product_sales mechanisms may use the legacy sales calculator. Do not manufacture
an exact quotation or treat text saying something is NOT sold as permission to sell it.
Proposed additional opportunities stay outside calculated income until the user requests
a separate scenario. Price/term assumptions may be proposed within the stated mechanism,
but they must never create another revenue source. Missing prices do not change the
category. If commercial intent is absent, conflicting or ambiguous, set needs_clarification,
return no income lines, and ask a short targeted question; do not assume product sales or
zero business income. A separately supplied USER REVENUE DESCRIPTION is the user's explicit
commercial statement; if other text contradicts it, ask rather than silently resolve it.
"""


def validate_intent(config, description, *, require=False):
    if require and config.get("intent_source") == "user_override":
        raise ValueError("An AI proposal cannot claim to be an explicit user edit")
    intent = config.get("commercial_intent")
    if intent is None:
        if require:
            raise ValueError("User revenue-method interpretation is required")
        return  # Existing saved/manual inputs are not silently reclassified.
    from backend.orchestration.equipment_advisor import validate

    validate(intent, SCHEMA)
    mechanisms = {}
    for m in intent["mechanisms"]:
        if not m["id"].strip() or m["id"] in mechanisms:
            raise ValueError("Revenue mechanism IDs must be unique")
        if not m["context_quote"].strip() or not (
            m["context_quote"].casefold() in description.casefold()
            or config.get("intent_source") == "user_override"
            and m["context_quote"] == config.get("intent_override_reason")
        ):
            raise ValueError("Revenue mechanisms require exact user-context evidence")
        if not m["interpretation"].strip():
            raise ValueError("Revenue mechanism reasoning required")
        mechanisms[m["id"]] = m
    lines = [(s, "product_sales") for s in config.get("sales", [])] + [
        (s, s["category"]) for s in config.get("commercial_lines", [])
    ]
    if intent["status"] == "needs_clarification":
        if lines or not intent["questions"]:
            raise ValueError(
                "Unclear commercial intent needs questions, not assumed sales"
            )
        return
    if not mechanisms:
        raise ValueError(
            "Explicit commercial intent needs at least one stated mechanism"
        )
    covered = set()
    for line, category in lines:
        identifier = line.get("intent_id")
        mechanism = mechanisms.get(identifier)
        if mechanism is None:
            raise ValueError(
                "Calculated revenue has no user-stated mechanism: "
                + line.get("name", line.get("id", ""))
            )
        if category != mechanism["category"]:
            raise ValueError(
                "Revenue category contradicts user method: " + line.get("name", "")
            )
        covered.add(identifier)
    if covered != set(mechanisms):
        raise ValueError(
            "Some user-stated revenue methods were omitted from the proposal"
        )


def require_resolved_intent(config, description):
    validate_intent(config, description)
    intent = config.get("commercial_intent") or {}
    if intent.get("status") == "needs_clarification":
        raise ValueError(
            "Revenue method needs clarification: " + "; ".join(intent["questions"])
        )


def capture_manual_methods(config, reason, *, revenue_box=None):
    """An explicit saved user edit may revise the interpreted commercial strategy."""
    if "commercial_intent" not in config:
        return config
    rows = [(s, "product_sales") for s in config.get("sales", [])] + [
        (s, s["category"]) for s in config.get("commercial_lines", [])
    ]
    mechanisms = []
    for line, category in rows:
        line["intent_id"] = line["id"]
        if revenue_box is not None and not line.get("context_quote"):
            line["context_quote"] = revenue_box
        mechanisms.append(
            {
                "id": line["id"],
                "category": category,
                "context_quote": reason if revenue_box is None else revenue_box,
                "interpretation": "Explicit user-edited revenue line: "
                + line.get("name", line["id"]),
            }
        )
    config["intent_source"] = "user_override"
    config["intent_override_reason"] = reason
    config["commercial_intent"] = {
        "status": "explicit" if mechanisms else "needs_clarification",
        "mechanisms": mechanisms,
        "questions": []
        if mechanisms
        else [
            "How does this project earn income? No revenue lines are currently included."
        ],
    }
    return config
