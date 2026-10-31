"""Reference manifest only. No legacy formulas, values or automatic defaults."""

REFERENCE = {
    "filename": "Task 2 Charlie Economics 2.xlsx",
    "sha256": "bff6c13a62c5d9e83cd7a00c79b2ce4c4db2042fc37312676efe6e450080cca0",
    "worksheet": "Opex",
    "purpose": "Founder workflow reference; unvalidated; not a selectable costing model",
    "observed_sections": {
        "A3": "Utilities",
        "A7": "Staffing",
        "A16": "Raw materials and delivery/storage",
        "A32": "Maintenance",
        "A41": "Waste management",
        "A44": "Packaging",
        "A47": "Marketing",
        "A50": "Insurance",
        "A52": "Taxes",
        "A56": "Research and development",
        "A59": "Emergency allowance",
        "A62:A63": "Fixed/variable categorisation",
    },
    "differences": (
        "Spreadsheet combines some delivery/storage with raw materials; reconcile packaging/storage before adding costs.",
        "Spreadsheet maintenance, insurance and waste allowances have different bases/rates; never override Garrett automatically.",
        "Staff job titles span operating, support and supervisory roles; do not use all staff as operating-labor-only base.",
        "Emergency allowance is not a default Garrett factor. Distinguish contingent cash expense from reserves or working capital.",
        "Tax exemptions and local risk claims require evidence, not automatic acceptance.",
    ),
}
