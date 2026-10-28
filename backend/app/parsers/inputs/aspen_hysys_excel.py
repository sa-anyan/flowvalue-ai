"""Aspen HYSYS Excel-export adapter: canonical evidence only.

Independent implementation for property-in-rows HYSYS result tables:
    Property | Units | Stream A | Stream B | ...

No vendor software is executed; no spreadsheet formulas are evaluated.
No equipment sizing, economic calculations, or formatted workbook output.
The source repository Mo-Somji/HYSYS-ME-Balance-Formatting was studied as a
behavioural reference, but its code is not copied (no licence supplied).
"""

from app.parsers.balance.models import Entity
from app.parsers.balance.parser import Parser, property_info
from app.parsers.balance.units import clean, unit_key
from app.parsers.balance.workbook import address

# =============================================================================
# 01 — INPUT FORMAT AND DETECTION
# =============================================================================

_MAIN = {
    "phase": ("phase", None),
    "temperature": ("temperature", "temperature"),
    "pressure": ("pressure", "pressure"),
    "mass density": ("density", "density"),
    "molar enthalpy": ("specific_enthalpy", "enthalpy"),
    "mole enthalpy": ("specific_enthalpy", "enthalpy"),
    "mass enthalpy": ("specific_enthalpy", "enthalpy"),
    "mass flows": ("mass_flow", "mass_flow"),
    "mass flow": ("mass_flow", "mass_flow"),
    "mole flows": ("molar_flow", "molar_flow"),
    "molar flows": ("molar_flow", "molar_flow"),
    "mole flow": ("molar_flow", "molar_flow"),
    "molar flow": ("molar_flow", "molar_flow"),
}

_STOP = {
    "vapour phase", "vapor phase", "liquid phase", "aqueous phase",
    "solid phase", "overall", "other properties", "energy streams",
}
_MASS_UNITS = {"kg/h", "kg/s", "kg/min", "g/h", "g/s", "t/h", "lb/h", "lb/s"}
_MOLE_UNITS = {"kmol/h", "kmol/s", "mol/s", "mol/h", "lbmol/h"}


def _find_matrix(sheet):
    """Locate a HYSYS-style matrix by evidence, never by fixed row numbers."""
    for row in range(1, min(sheet.rows, 30) + 1):
        for col in range(1, min(sheet.cols - 2, 4) + 1):
            if clean(sheet.text(row, col + 1)) not in ("units", "unit"):
                continue
            streams = [
                cc for cc in range(col + 2, sheet.cols + 1)
                if sheet.text(row, cc)
            ]
            if not streams:
                continue
            labels = {
                clean(sheet.text(rr, col))
                for rr in range(row + 1, min(sheet.rows, row + 150) + 1)
            }
            if ({"temperature", "pressure"} <= labels
                    and ("mass flows" in labels or "mole flows" in labels
                         or "mass flow" in labels or "mole flow" in labels)):
                return row, col, streams
    return None


# =============================================================================
# 02 — CANONICAL EXTRACTION AND SOURCE LINEAGE
# =============================================================================


class HYSYSExcelParser(Parser):
    """Uses FlowValue's bounded workbook reader and evidence/issue builder."""

    def __init__(self, content, filename):
        super().__init__(content, filename)
        self.hysys_detected = False

    def tables(self, sheet, inferred):
        layout = _find_matrix(sheet)
        if layout is None:
            return super().tables(sheet, inferred)
        self.hysys_detected = True
        header_row, label_col, stream_cols = layout
        units_col = label_col + 1

        # A property group can contain components with the same declared units.
        # Never infer a component's basis without an explicit parent group.
        observations = []
        section = None
        for row in range(header_row + 1, sheet.rows + 1):
            label = sheet.text(row, label_col)
            key = clean(label)
            if not key:
                if not any(sheet.text(row, c) for c in stream_cols):
                    section = None
                continue
            if key in _STOP:
                section = None
                continue
            if key in ("mass flows", "mass flow"):
                section = "mass_flow"
            elif key in ("mole flows", "molar flows", "mole flow", "molar flow"):
                section = "molar_flow"
            unit = sheet.text(row, units_col) or None
            prop, dimension = _MAIN.get(key, (None, None))
            component = None

            if prop is None:
                # Component rows inside an explicit HYSYS flow section
                # inherit that section's declared basis, not an assumed basis.
                if section and unit_key(unit) in (
                    _MASS_UNITS if section == "mass_flow" else _MOLE_UNITS
                ):
                    prop, dimension, component = section, section, label
                    observations.append((row, label, prop, dimension, unit, component))
                    continue
                matched_prop, matched_dim, matched_component = property_info(label)
                if matched_prop and matched_dim:
                    prop, dimension, component = (
                        matched_prop, matched_dim, matched_component
                    )
                    # Do not re-label an explicit property as a component.
                    if prop not in ("mass_flow", "molar_flow"):
                        section = None
                elif section and unit_key(unit) in (
                    _MASS_UNITS if section == "mass_flow" else _MOLE_UNITS
                ):
                    prop, dimension, component = section, section, label
                else:
                    # Unrecognised component units and sections stay unmapped.
                    self.issue(
                        "hysys_unmapped_property",
                        f"{sheet.name}!{address(row, label_col)}: HYSYS property "
                        "or component basis not recognised.",
                    )
                    continue
            elif prop not in ("mass_flow", "molar_flow"):
                section = None

            observations.append((row, label, prop, dimension, unit, component))

        if not observations:
            self.issue(
                "hysys_no_properties",
                f"{sheet.name}: stream headers found but no supported properties.",
            )
            return

        last_row = observations[-1][0]
        table = self.new_table(
            sheet, header_row, label_col, last_row, stream_cols[-1],
            "material", "records_in_columns",
        )
        for col in stream_cols:
            identifier = sheet.text(header_row, col)
            if not identifier:
                continue
            id_evidence = self.evidence(
                sheet, header_row, col, "HYSYS stream header", "identifier",
                headers=[address(header_row, label_col)], inferred=inferred,
            )
            entity = Entity(
                key=f"{table.id}:{col}", kind="material",
                identifier=identifier, table=table.id,
                id_evidence=id_evidence,
            )
            for row, label, prop, dim, unit, component in observations:
                if not sheet.text(row, col) and sheet.cell(row, col).formula is None:
                    continue
                entity.values.append(
                    self.evidence(
                        sheet, row, col, label, prop,
                        dim, unit, component,
                        headers=[address(row, label_col), address(row, units_col)],
                        inferred=inferred,
                    )
                )
            if not entity.values:
                self.issue(
                    "hysys_empty_stream",
                    f"{sheet.name}!{address(header_row, col)}: stream header "
                    "has no extracted numeric or phase evidence.",
                    [id_evidence.id],
                )
            self.report.entities.append(entity)


# =============================================================================
# 03 — UNIT CONVERSION AND VALIDATION
# =============================================================================
# FlowValue's Parser.evidence() normalises only explicitly supported units
# and records original label, cell, value, unit, status and formula cache.
# Parser.run() performs the existing conservative consistency checks.
# Missing/unrecognised properties are not reconstructed by a model.


# =============================================================================
# 04 — CANONICAL OUTPUT ONLY
# =============================================================================


def parse_hysys_excel(content: bytes, filename: str):
    """Return the same BalanceReport consumed by FlowValue's existing Entry."""
    parser = HYSYSExcelParser(content, filename)
    report = parser.run()
    if not parser.hysys_detected:
        parser.issue(
            "hysys_layout_unrecognised",
            "No HYSYS-style property/units/stream matrix was confirmed. "
            "Generic Excel extraction, if any, requires operator review.",
        )
    return report


# =============================================================================
# 05 — OUT-OF-SCOPE
# =============================================================================
# No formatted Excel export, model execution, changes to the financial engine,
# equipment sizing, balance reconstruction, or copying of third-party code.
