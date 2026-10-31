"""Selectable Garrett pressure factors and explicitly disclosed vessel proxies.

PDF p.18 / printed p.268: vertical pressure-factor table and (P/50)**0.44.
PDF p.48 / printed p.298 explicitly refers pressure vessels to that table.
The agitated-tank page supplies no such instruction: its use is a proxy.
"""

from bisect import bisect_left
from dataclasses import asdict, dataclass
from math import isfinite

from ...models import positive
from ...unit_conversion import ConversionContext, Measurement, convert

PRESSURE_TABLE = (
    (50, 1.0),
    (100, 1.25),
    (200, 1.55),
    (300, 2.0),
    (400, 2.4),
    (500, 2.8),
    (600, 3.0),
    (700, 3.25),
    (800, 3.8),
    (900, 4.0),
    (1000, 4.2),
    (1500, 5.4),
    (2000, 6.5),
    (3000, 8.75),
    (4000, 11.25),
    (5000, 13.75),
)
REFERENCES = {
    "G268-031": (50.0, "source_vertical_column"),
    "G298-132": (250.0, "source_vessel_cross_reference"),
    "G258-004": (1500.0, "provisional_agitated_vessel_proxy"),
    "G258-005": (600.0, "provisional_agitated_vessel_proxy"),
    "G258-006": (300.0, "provisional_agitated_vessel_proxy"),
    "G258-007": (50.0, "provisional_agitated_vessel_proxy"),
}


@dataclass(frozen=True)
class PressureAdjustment:
    method: str
    target_design_pressure: Measurement
    reference_pressure_basis: str
    applicability_note: str
    atmospheric_pressure_pa: float | None = None
    allow_extrapolation: bool = False
    extrapolation_justification: str | None = None


def list_pressure_methods(curve_id):
    options = [
        {
            "id": "native_curve",
            "label": "Keep original pressure curve",
            "requires_target_pressure": False,
        }
    ]
    if curve_id not in REFERENCES:
        return options
    reference, classification = REFERENCES[curve_id]
    for method, label in [
        ("garrett_power", "Garrett pressure power relationship"),
        ("garrett_table_linear", "Garrett table with linear interpolation"),
    ]:
        options.append(
            {
                "id": method,
                "label": label
                + (" — agitated-vessel proxy" if "proxy" in classification else ""),
                "reference_pressure_psi": reference,
                "applicability": classification,
                "requires_explicit_pressure_basis": True,
                "requires_applicability_note": True,
                "source_printed_page": 268,
                "source_pdf_page": 18,
                "table_range_psi": [50, 5000],
                "range_basis": "Table envelope used as a screening guard, not a validated power-correlation applicability range",
                "formula": "C(P2) = C(P1) * F(P2) / F(P1)",
                "factor_formula": "F(P) = (P / 50 psi)**0.44"
                if method == "garrett_power"
                else "Piecewise linear interpolation between tabulated factors; interpolation choice is an implementation assumption",
                "warning": "Agitated-tank use is an engineering proxy, not a Garrett instruction for agitated tanks"
                if "proxy" in classification
                else "Historical preliminary pressure correction; review source applicability",
            }
        )
    return options


def pressure_factor(pressure_psi, method):
    p = positive(pressure_psi, "pressure psi")
    if method == "garrett_power":
        return (p / 50) ** 0.44
    if method != "garrett_table_linear":
        raise ValueError("Unknown pressure method")
    if not 50 <= p <= 5000:
        raise ValueError(
            "Table extrapolation is unsupported; select an explicitly justified power method instead"
        )
    i = bisect_left([row[0] for row in PRESSURE_TABLE], p)
    if PRESSURE_TABLE[i][0] == p:
        return PRESSURE_TABLE[i][1]
    low, high = PRESSURE_TABLE[i - 1], PRESSURE_TABLE[i]
    return low[1] + (p - low[0]) / (high[0] - low[0]) * (high[1] - low[1])


def adjust_pressure(curve_id, amount, request, *, allow_unverified):
    if not isinstance(request, PressureAdjustment):
        raise TypeError("pressure_adjustment must be PressureAdjustment")
    if curve_id not in REFERENCES:
        raise ValueError(
            "No pressure-adjustment basis is registered for this configuration; open tanks cannot become pressure vessels"
        )
    if request.method not in ["garrett_power", "garrett_table_linear"]:
        raise ValueError("Choose a registered pressure-adjustment method")
    if not allow_unverified:
        raise ValueError(
            "Pressure scenarios require explicit provisional-data approval"
        )
    if (
        not isinstance(request.applicability_note, str)
        or not request.applicability_note.strip()
    ):
        raise ValueError(
            "Pressure adjustment requires a recorded applicability justification"
        )
    if request.reference_pressure_basis not in ["gauge", "absolute"]:
        raise ValueError(
            "Explicit reference pressure basis (gauge or absolute) is required; source psi label alone does not establish it"
        )
    if type(request.allow_extrapolation) is not bool:
        raise ValueError("allow_extrapolation must be boolean")
    target = request.target_design_pressure
    if not isinstance(target, Measurement):
        raise TypeError("Target design pressure must be a Measurement")
    conversion = convert(
        target.value,
        target.unit,
        "psi",
        pressure_basis=target.pressure_basis,
        source=target.source,
        context=ConversionContext(
            target_pressure_basis=request.reference_pressure_basis,
            atmospheric_pressure_pa=request.atmospheric_pressure_pa,
        ),
    )
    if conversion.status != "converted":
        raise ValueError("; ".join(conversion.issues))
    p2 = positive(conversion.value, "target design pressure")
    p1, classification = REFERENCES[curve_id]
    outside = not (50 <= p1 <= 5000 and 50 <= p2 <= 5000)
    if outside and (
        request.method != "garrett_power"
        or not request.allow_extrapolation
        or not isinstance(request.extrapolation_justification, str)
        or not request.extrapolation_justification.strip()
    ):
        raise ValueError(
            "Pressure outside table envelope needs explicitly justified power-law extrapolation; table extrapolation is not supported"
        )
    f1 = pressure_factor(p1, request.method)
    anchor_pressure = min(max(p2, 50.0), 5000.0)
    anchor_factor = pressure_factor(anchor_pressure, request.method)
    f2 = (
        anchor_factor * (p2 / anchor_pressure) ** 0.44
        if outside
        else pressure_factor(p2, request.method)
    )
    multiplier = f2 / f1
    adjusted = positive(
        positive(amount, "reference equipment cost") * multiplier,
        "pressure-adjusted equipment cost",
    )
    if not isfinite(multiplier):
        raise ValueError("Pressure multiplier exceeds numerical limits")
    evidence = {
        "method": request.method,
        "applicability": classification,
        "applicability_note": request.applicability_note,
        "reference_pressure_psi": p1,
        "target_pressure_psi": p2,
        "reference_pressure_basis": request.reference_pressure_basis,
        "reference_pressure_basis_source": "Explicit caller interpretation; the source psi label alone does not establish gauge/absolute basis",
        "target_conversion": asdict(conversion),
        "reference_factor": f1,
        "target_factor": f2,
        "multiplier": multiplier,
        "baseline_equipment_cost": amount,
        "adjusted_equipment_cost": adjusted,
        "formula": "C(P2) = C(P1) * F(P2) / F(P1)",
        "source_printed_page": 268,
        "source_pdf_page": 18,
        "source_cross_reference_printed_page": 298
        if classification == "source_vessel_cross_reference"
        else None,
        "interpolation_basis": "Linear interpolation in psi between table entries is an implementation assumption"
        if request.method == "garrett_table_linear"
        else None,
        "anchor_pressure_psi": anchor_pressure if outside else None,
        "anchor_factor": anchor_factor if outside else None,
        "extrapolated": outside,
        "extrapolation_justification": request.extrapolation_justification
        if outside
        else None,
        "range_basis": "50–5000 psi table envelope; not source-validated power-law limits",
        "installation_basis": "Installation factor held at selected equipment-family value; not independently calibrated versus pressure",
        "warning": "Engineering proxy for agitated tanks; no mechanical design or pressure-rating certification"
        if "proxy" in classification
        else "Source applicability requires review; not a pressure-vessel design calculation",
    }
    return adjusted, evidence
