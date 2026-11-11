"""Normalize only the active UNIT-003 parameter families before native sizing.

No engineering equations or property assumptions live here. Original records,
including provenance and ranges, are copied rather than mutated. Other native
parameter contracts remain owned by engineering_sizing.registry.
"""

import copy
from dataclasses import asdict

from .unit_conversion import UnitResolutionError, convert

TARGETS = {
    "hydraulic_loading_m_h": "m/h",
    "overall_u_w_m2_k": "W/m2/K",
    "service_cycle_h": "h",
    "empty_bed_contact_time_min": "min",
    "residence_time_h": "h",
    "gas_residence_time_s": "s",
}


def normalize_parameters(parameters, *, context=None, native_spellings=None):
    """Return copied parameter records plus every numerical transformation.

    Bare numbers preserve the existing explicit-native-unit API. A typed record
    must state its unit; selected/low/high values all share that source unit.
    Missing bounds stay missing and no range or central estimate is invented.
    """
    normalized = copy.deepcopy(parameters)
    traces = []
    for name, record in normalized.items():
        if name not in TARGETS or not isinstance(record, dict):
            continue
        # Preserve the native adapter's existing numeric representation contract
        # (Decimal/Fraction/NumPy scalars included) without needless coercion.
        if native_spellings and record.get("unit") in native_spellings.get(name, ()):
            continue
        if "value" not in record:
            raise UnitResolutionError(name + ": selected value is required")
        target = TARGETS[name]
        for field in ("value", "low", "high"):
            if field not in record or (field != "value" and record[field] is None):
                continue
            result = convert(
                record[field],
                record.get("unit"),
                target,
                context=context,
                source=record.get("source", {}),
            )
            if result.value is None:
                raise UnitResolutionError(
                    name
                    + " unit mismatch or invalid "
                    + field
                    + ": "
                    + "; ".join(result.issues)
                )
            record[field] = result.value
            traces.append(
                {"parameter": name, "field": field, "conversion": asdict(result)}
            )
        record["unit"] = target
    return normalized, traces
