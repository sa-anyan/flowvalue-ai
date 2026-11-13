"""SLOT — Turton et al., Analysis, Synthesis and Design of Chemical Processes — cost of manufacturing (COM) factors and the operating-labour correlation.

Awaiting page-checked values. Add a row only from a page the founder supplies
or confirms (record the printed page/table), with status "page_checked". Until
then nothing here is used in any calculation. Do not type values from memory.
"""

METHOD = "turton"

# Example of the row shape (left empty on purpose):
# {"category": "maintenance", "base": "...", "low": None, "typical": None, "high": None,
#  "units": "...", "source": "...", "page": "...", "applicability": "...",
#  "status": "pending_source_check"}
ROWS = (
    {
        "category": "operating_labor",
        "kind": "correlation",
        "id": "turton_operators_per_shift",
        "base": "process equipment counts and solids-handling steps",
        "low": None, "typical": None, "high": None,
        "units": "operators per shift",
        "source": "Turton et al., operating-labour correlation",
        "page": None,
        "applicability": "Operators per shift from equipment counts; needs the printed equation and page before use.",
        "status": "pending_source_check",
    },
)
