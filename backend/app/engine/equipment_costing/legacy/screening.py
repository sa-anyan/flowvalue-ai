"""LEGACY compatibility engine. Retained for existing routes and saved projects.

New methods belong in equipment_costing/{source}/{equipment}.py; escalation is separate.
Screening estimates in USD, using Turton et al. log10 correlations.

Sources, validity ranges, exclusions and factor assumptions: docs/calculation_basis.md.
"""

from math import isfinite, log, log10, pi
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Positive = Annotated[float, Field(ge=1e-9, le=1e12)]
Material = Literal["carbon_steel", "stainless_steel"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class CostSettings(Model):
    cepci_basis: str = Field(
        default="Operator planning assumption; not a current licensed observation",
        max_length=1500,
    )
    capital_cost_multiplier: float = Field(default=1, ge=0.5, le=1.5)
    cepci_current: Positive = 800
    cepci_base: Positive = 397
    allow_extrapolation: bool = False


class EquipmentBase(Model):
    unit_id: str = Field(min_length=1, max_length=100, pattern=r"\S")
    material: Material = "carbon_steel"
    quantity: int = Field(default=1, ge=1, le=10000)
    material_factor_override: float | None = Field(default=None, ge=1, le=100)
    pressure_factor_override: float | None = Field(default=None, ge=1, le=100)


class HeatExchanger(EquipmentBase):
    kind: Literal["heat_exchanger"] = "heat_exchanger"
    duty_kw: Positive
    overall_u_w_m2_k: Positive
    lmtd_k: Positive
    lmtd_correction_factor: float = Field(default=1, gt=0, le=1)
    design_pressure_barg: float = Field(default=0, ge=0, le=1000)


class Vessel(EquipmentBase):
    kind: Literal["vessel", "reactor"] = "vessel"
    volume_m3: Positive
    height_diameter_ratio: float = Field(default=3, ge=1, le=10)
    design_pressure_barg: float = Field(default=0, ge=0, le=300)
    allowable_stress_mpa: float = Field(default=94.4, gt=0, le=1000)
    weld_efficiency: float = Field(default=0.9, gt=0, le=1)
    corrosion_allowance_mm: float = Field(default=3.15, ge=0, le=50)
    minimum_thickness_mm: float = Field(default=6.3, gt=0, le=100)


class Pump(EquipmentBase):
    kind: Literal["pump"] = "pump"
    volumetric_flow_m3_h: Positive
    density_kg_m3: Positive
    head_m: Positive
    efficiency: float = Field(default=0.75, gt=0, le=1)
    design_pressure_barg: float = Field(default=0, ge=0, le=1000)


class Compressor(EquipmentBase):
    kind: Literal["compressor"] = "compressor"
    mass_flow_kg_s: Positive
    inlet_temperature_k: Positive
    inlet_pressure_bar_abs: Positive
    outlet_pressure_bar_abs: Positive
    molecular_weight_kg_kmol: Positive
    heat_capacity_ratio: float = Field(default=1.4, gt=1, le=1.67)
    isentropic_efficiency: float = Field(default=0.75, gt=0, le=1)

    @model_validator(mode="after")
    def pressure_rise(self):
        if self.outlet_pressure_bar_abs <= self.inlet_pressure_bar_abs:
            raise ValueError("Compressor outlet pressure must exceed inlet pressure")
        return self


class QuotedEquipment(EquipmentBase):
    kind: Literal["quoted"] = "quoted"
    purchased_cost_usd: Positive
    installed_cost_usd: Positive
    reference_cepci: Positive = 800
    source: str = Field(min_length=1, max_length=2000)


Equipment = Annotated[
    HeatExchanger | Vessel | Pump | Compressor | QuotedEquipment,
    Field(discriminator="kind"),
]


class CostingRequest(Model):
    equipment: list[Equipment] = Field(min_length=1, max_length=1000)
    settings: CostSettings = Field(default_factory=CostSettings)

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [unit.unit_id.strip() for unit in self.equipment]
        if len(ids) != len(set(ids)):
            raise ValueError("Equipment unit_id values must be unique")
        return self


class EquipmentCost(Model):
    unit_id: str
    kind: str
    material: Material
    quantity: int
    sizing: dict[str, float]
    correlation_key: str
    correlation_size: float
    correlation_size_unit: str
    valid_size_range: tuple[float, float]
    material_factor: float
    pressure_factor: float
    bare_module_factor: float
    base_purchase_cost_usd: float
    indexed_base_purchase_cost_usd: float
    purchased_equipment_cost_usd: float
    bare_module_cost_usd: float
    warnings: list[str]


class EquipmentBOM(Model):
    currency: Literal["USD"] = "USD"
    settings: CostSettings
    items: list[EquipmentCost]
    total_purchased_equipment_cost_usd: float
    total_bare_module_cost_usd: float
    assumptions: list[str]


from app.engine.equipment_costing.turton_et_al import (
    CORRELATIONS,
    MATERIAL_FACTORS,
    base_purchase_cost,
)


def lmtd(delta_t1_k: float, delta_t2_k: float) -> float:
    """Positive terminal differences only; equal differences have a finite limit."""
    if not all(isfinite(x) and x > 0 for x in (delta_t1_k, delta_t2_k)):
        raise ValueError(
            "LMTD requires finite, positive terminal temperature differences"
        )
    if abs(delta_t1_k - delta_t2_k) <= 1e-10 * max(delta_t1_k, delta_t2_k):
        return (delta_t1_k + delta_t2_k) / 2
    return (delta_t1_k - delta_t2_k) / (log(delta_t1_k) - log(delta_t2_k))


def size_equipment(unit: Equipment) -> tuple[float, dict[str, float]]:
    if isinstance(unit, HeatExchanger):
        area = (
            unit.duty_kw
            / unit.overall_u_w_m2_k
            / unit.lmtd_k
            / unit.lmtd_correction_factor
            * 1000
        )
        return area, {"area_m2": area}
    if isinstance(unit, Vessel):
        diameter = (4 * unit.volume_m3 / (pi * unit.height_diameter_ratio)) ** (1 / 3)
        pressure_mpa = unit.design_pressure_barg / 10
        denominator = 2 * (
            unit.allowable_stress_mpa * unit.weld_efficiency - 0.6 * pressure_mpa
        )
        if denominator <= 0:
            raise ValueError(
                f"{unit.unit_id}: design pressure exceeds allowable stress basis"
            )
        thickness = max(
            unit.minimum_thickness_mm / 1000,
            pressure_mpa * diameter / denominator + unit.corrosion_allowance_mm / 1000,
        )
        if thickness / diameter > 0.1:
            raise ValueError(
                f"{unit.unit_id}: thick-wall design outside screening model"
            )
        return unit.volume_m3, {
            "diameter_m": diameter,
            "cylindrical_height_m": unit.height_diameter_ratio * diameter,
            "wall_thickness_mm": thickness * 1000,
        }
    if isinstance(unit, Pump):
        delta_p_pa = unit.density_kg_m3 * 9.80665 * unit.head_m
        hydraulic_kw = unit.volumetric_flow_m3_h / 3600 * delta_p_pa / 1000
        return hydraulic_kw / unit.efficiency, {
            "head_m": unit.head_m,
            "differential_pressure_bar": delta_p_pa / 1e5,
            "hydraulic_power_kw": hydraulic_kw,
            "shaft_power_kw": hydraulic_kw / unit.efficiency,
        }
    ratio = unit.outlet_pressure_bar_abs / unit.inlet_pressure_bar_abs
    k = unit.heat_capacity_ratio
    head = (
        k
        / (k - 1)
        * (8314.462618 / unit.molecular_weight_kg_kmol)
        * unit.inlet_temperature_k
        * (ratio ** ((k - 1) / k) - 1)
    )
    fluid_kw = unit.mass_flow_kg_s * head / 1000
    return fluid_kw, {
        "pressure_ratio": ratio,
        "isentropic_head_j_kg": head,
        "fluid_power_kw": fluid_kw,
        "shaft_power_kw": fluid_kw / unit.isentropic_efficiency,
    }


def cost_equipment(unit: Equipment, settings: CostSettings) -> EquipmentCost:
    if isinstance(unit, QuotedEquipment):
        factor = (
            settings.cepci_current
            / unit.reference_cepci
            * settings.capital_cost_multiplier
        )
        return EquipmentCost(
            unit_id=unit.unit_id,
            kind="quoted",
            material=unit.material,
            quantity=unit.quantity,
            sizing={},
            correlation_key="quoted",
            correlation_size=1,
            correlation_size_unit="quoted unit",
            valid_size_range=(1, 1),
            material_factor=1,
            pressure_factor=1,
            bare_module_factor=unit.installed_cost_usd / unit.purchased_cost_usd,
            base_purchase_cost_usd=unit.purchased_cost_usd,
            indexed_base_purchase_cost_usd=unit.purchased_cost_usd
            * settings.cepci_current
            / unit.reference_cepci,
            purchased_equipment_cost_usd=unit.purchased_cost_usd * factor,
            bare_module_cost_usd=unit.installed_cost_usd * factor,
            warnings=[
                f"External quote/model: {unit.source}",
                f"Reference CEPCI {unit.reference_cepci}; pressure/material factors embedded in imported costs; material dropdown does not re-price external estimates.",
            ],
        )
    key = "vessel" if unit.kind == "reactor" else unit.kind
    _k1, _k2, _k3, b1, b2, lower, upper, size_unit = CORRELATIONS[key]
    size, sizing = size_equipment(unit)
    warnings = []
    if not isfinite(size) or size <= 0:
        raise ValueError(f"{unit.unit_id}: invalid derived equipment size")
    if not lower <= size <= upper:
        message = f"{unit.unit_id}: {size:g} {size_unit} outside correlation range [{lower}, {upper}]"
        if not settings.allow_extrapolation:
            raise ValueError(message)
        warnings.append(message + "; extrapolation explicitly enabled")
    fm = unit.material_factor_override or MATERIAL_FACTORS[key][unit.material]
    fp = 1.0
    if isinstance(unit, Vessel):
        diameter = sizing["diameter_m"]
        if not 0.3 <= diameter <= 4:
            message = f"{unit.unit_id}: diameter outside vessel pressure-factor range [0.3, 4] m"
            if not settings.allow_extrapolation:
                raise ValueError(message)
            warnings.append(message + "; extrapolation explicitly enabled")
        fp = max(
            1,
            (
                (
                    (unit.design_pressure_barg + 1)
                    * diameter
                    / (2 * (850 - 0.6 * (unit.design_pressure_barg + 1)))
                )
                + 0.00315
            )
            / 0.0063,
        )
        warnings.append(
            "Cylinder and thin-wall screening only; heads, internals and code design excluded"
        )
        if unit.kind == "reactor":
            warnings.append(
                "Reactor is a vertical vessel-shell proxy; agitator, catalyst and internals excluded"
            )
    elif isinstance(unit, HeatExchanger):
        p = unit.design_pressure_barg
        if p > 5:
            fp = max(1, 10 ** (-0.00164 - 0.00627 * log10(p) + 0.0123 * log10(p) ** 2))
        if p > 140 and unit.pressure_factor_override is None:
            raise ValueError(
                f"{unit.unit_id}: exchanger above 140 barg requires pressure_factor_override"
            )
    elif isinstance(unit, Pump):
        # Pressure correction uses discharge/design pressure, not differential pressure alone.
        p = max(unit.design_pressure_barg, sizing["differential_pressure_bar"])
        if p > 10:
            fp = max(1, 10 ** (-0.3935 + 0.3957 * log10(p) - 0.00226 * log10(p) ** 2))
        if p > 100 and unit.pressure_factor_override is None:
            raise ValueError(
                f"{unit.unit_id}: pump above 100 barg requires pressure_factor_override"
            )
        warnings.append(
            "Separate motor, NPSH and pump curve selection excluded; stainless Fm=2.3 is a planning assumption"
        )
    else:
        warnings.append(
            "Single-stage ideal gas; compressor driver excluded; pressure effect enters fluid power, Fp=1"
        )
    if (
        unit.material_factor_override is not None
        or unit.pressure_factor_override is not None
    ):
        warnings.append("User-supplied factor override applied")
    fp = unit.pressure_factor_override or fp
    base = base_purchase_cost(
        key, size, allow_extrapolation=settings.allow_extrapolation
    )
    indexed = base * settings.cepci_current / settings.cepci_base
    fbm = b1 + b2 * fm * fp
    return EquipmentCost(
        unit_id=unit.unit_id,
        kind=unit.kind,
        material=unit.material,
        quantity=unit.quantity,
        sizing=sizing,
        correlation_key=f"turton_2001_{key}",
        correlation_size=size,
        correlation_size_unit=size_unit,
        valid_size_range=(lower, upper),
        material_factor=fm,
        pressure_factor=fp,
        bare_module_factor=fbm,
        base_purchase_cost_usd=base,
        indexed_base_purchase_cost_usd=indexed,
        purchased_equipment_cost_usd=indexed
        * fm
        * fp
        * settings.capital_cost_multiplier,
        bare_module_cost_usd=indexed * fbm * settings.capital_cost_multiplier,
        warnings=warnings,
    )


def build_bom(request: CostingRequest) -> EquipmentBOM:
    items = [cost_equipment(unit, request.settings) for unit in request.equipment]
    return EquipmentBOM(
        settings=request.settings,
        items=items,
        total_purchased_equipment_cost_usd=sum(
            x.quantity * x.purchased_equipment_cost_usd for x in items
        ),
        total_bare_module_cost_usd=sum(
            x.quantity * x.bare_module_cost_usd for x in items
        ),
        assumptions=[
            "Per-item costs are per unit; totals include quantity",
            f"Capital stress multiplier {request.settings.capital_cost_multiplier:g} applied to purchased and bare module costs; this is a scenario, not a probability",
            f"CEPCI target/reference {request.settings.cepci_current:g}/{request.settings.cepci_base:g}. Source basis (user supplied): {request.settings.cepci_basis}",
            "Bare module totals exclude offsites, working capital, contingency and owner costs",
            "Sources and validity: docs/calculation_basis.md",
        ],
    )
