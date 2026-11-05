"""Explicit drawer choices become user-supplied routing, never AI interpretation."""
from .validation import CATEGORIES


def bind_manual_lines(state, config):
    statements, mechanisms, ids = [], [], set()
    active = [(s, "product_sales") for s in config.get("sales", [])] + [(s, s.get("category")) for s in config.get("commercial_lines", [])]
    for line, category in active:
        from .method_forms import validate_form_line
        validate_form_line(line, config.get("financial", {}).get("operating_years", 0))
        if category not in CATEGORIES:
            raise ValueError("Choose one of the six MECE revenue types")
        identifier = line.get("id")
        if not identifier or identifier in ids or not str(line.get("name", "")).strip():
            raise ValueError("Revenue lines need unique IDs and names")
        ids.add(identifier)
        quote = "User-selected " + category.replace("_", " ") + ": " + line["name"] + "."
        statements.append(quote)
        line["intent_id"], line["context_quote"] = identifier, quote
        mechanisms.append({"id": identifier, "category": category, "context_quote": quote,
                           "interpretation": "Explicit user selection in the revenue drawer"})
    for pending in config.get("pending_inputs", []):
        if pending.get("category") == "avoided_cost":
            continue
        if pending.get("id") in ids:
            raise ValueError("A pending payment cannot also be an active payment")
        mechanisms.append({"id": pending["id"], "category": pending["category"],
                           "context_quote": pending["context_quote"], "interpretation": "Pending user-reviewed opportunity"})
    text = state.get("revenue_description", "")
    additions = [quote for quote in statements if quote not in text]
    if additions:
        text += "\n\nExplicit drawer selections (current calculation routes):\n" + "\n".join(additions)
    state["revenue_description"] = text
    state["description"] = state.get("process_description", "") + "\n\nUSER REVENUE DESCRIPTION:\n" + text
    config["commercial_intent"] = {"status": "explicit" if mechanisms else "needs_clarification", "mechanisms": mechanisms,
                                   "questions": [] if mechanisms else ["Add at least one payment method"]}
    config["intent_source"] = "user_override"
    state.pop("revenue_approval", None)
    return config
