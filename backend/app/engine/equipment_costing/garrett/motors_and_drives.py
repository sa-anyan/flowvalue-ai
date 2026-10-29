"""MOTORS AND DRIVES

Canonical Garrett chart group: garrett-a1-293.
Chemical Engineering Economics (1989), Appendix 1, printed page 293.
Reference basis: CE Index 320, early 1987. No cost curve is implemented yet.
Source references preserve both supplied PDFs; these are not independent methods.
Implement only after reviewing equation/curve, inputs, units, range and scope.
"""

CATALOG_ID = "garrett-a1-293"
EQUIPMENT_NAME = "Motors and drives"
IMPLEMENTATION_STATUS = "not_implemented"
SOURCE_REFERENCES = [
    {"source_id": "garrett-1989-appendix-1", "pdf_page": 43, "printed_page": 293},
    {"source_id": "garrett-1989-full-text", "pdf_page": 304, "printed_page": 293},
]


def estimate_base_price(*, equipment_id: str, **design_inputs):
    raise NotImplementedError(
        f"{equipment_id}: Garrett {EQUIPMENT_NAME} ({CATALOG_ID}) is not implemented. "
        "A reviewed equation/curve, size basis, units and source reference are required."
    )
