"""Commercial context provenance; user arrangements need an exact supplied quote."""


def verify_context(line, description):
    quote = line.get("context_quote", "")
    if line.get("arrangement") == "user_confirmed" and (
        not quote.strip() or quote.casefold() not in description.casefold()
    ):
        raise ValueError(
            "Confirmed user arrangement requires an exact process-context quote"
        )
    if quote and quote.casefold() not in description.casefold():
        raise ValueError(
            "Commercial context quote does not occur in project description"
        )
