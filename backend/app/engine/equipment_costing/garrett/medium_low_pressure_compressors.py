"""MEDIUM / LOW PRESSURE COMPRESSORS

Canonical Garrett chart group: garrett-a1-271.
Chemical Engineering Economics (1989), Appendix 1, printed page 271.
Reference basis: CE Index 320, early 1987. No cost curve is implemented yet.
Source references preserve both supplied PDFs; these are not independent methods.
Implement only after reviewing equation/curve, inputs, units, range and scope.
"""

CATALOG_ID = "garrett-a1-271"
EQUIPMENT_NAME = "Medium / low pressure compressors"
IMPLEMENTATION_STATUS = "not_implemented"
SOURCE_REFERENCES = [
    {"source_id": "garrett-1989-appendix-1", "pdf_page": 21, "printed_page": 271},
    {"source_id": "garrett-1989-full-text", "pdf_page": 282, "printed_page": 271},
]


def estimate_base_price(*, equipment_id: str, **design_inputs):
    raise NotImplementedError(
        f"{equipment_id}: Garrett {EQUIPMENT_NAME} ({CATALOG_ID}) is not implemented. "
        "A reviewed equation/curve, size basis, units and source reference are required."
    )
