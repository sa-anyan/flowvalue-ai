"""Explicit library adapters. Never import or execute user-supplied Python/pickle."""

import warnings
from importlib.metadata import version
from typing import Literal

from pydantic import Field

from app.engine.costing import Model, QuotedEquipment


class OpenPyTEARequest(Model):
    name: str = Field(min_length=1, max_length=100)
    parameter: float = Field(gt=0, le=1e12)
    process_type: str = Field(default="Fluids", max_length=100)
    category: str = Field(max_length=150)
    equipment_type: str = Field(max_length=150)
    material: str = Field(default="Carbon steel", max_length=100)
    target_year: int = Field(default=2024, ge=1947, le=2100)


def openpytea_equipment(request: OpenPyTEARequest) -> dict:
    from openpytea.equipment import CEPCI_DF, Equipment

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        eq = Equipment(
            name=request.name,
            param=request.parameter,
            process_type=request.process_type,
            category=request.category,
            type=request.equipment_type,
            material=request.material,
            target_year=request.target_year,
        )
    library_notes = [str(w.message)[:400] for w in captured]

    cepci = float(CEPCI_DF.loc[request.target_year, "cepci"])
    quoted = QuotedEquipment(
        unit_id=request.name,
        purchased_cost_usd=float(eq.purchased_cost),
        installed_cost_usd=float(eq.direct_cost),
        reference_cepci=cepci,
        source=(
            f"OpenPyTEA {version('openpytea')}, {request.category}/{request.equipment_type}, {request.material}, {request.process_type}, target {request.target_year}. "
            + " ".join(library_notes)
        )[:2000],
    )
    return {
        "equipment": quoted.model_dump(),
        "library": "OpenPyTEA",
        "version": version("openpytea"),
        "warning": "External direct-cost basis differs from Turton bare-module basis. Review scope before combining estimates. "
        + " ".join(library_notes),
        "library_warnings": library_notes,
    }


class ExternalUnit(Model):
    unit_id: str = Field(min_length=1, max_length=100)
    purchased_cost_usd: float = Field(gt=0, le=1e15)
    installed_cost_usd: float = Field(gt=0, le=1e15)


class BioSTEAMSnapshot(Model):
    schema_version: Literal["flowvalue-biosteam-v1"]
    library_version: str = Field(min_length=1, max_length=50)
    reference_cepci: float = Field(gt=0, le=1e6)
    provenance: str = Field(min_length=1, max_length=2000)
    equipment: list[ExternalUnit] = Field(min_length=1, max_length=1000)
    fixed_opex_usd_per_year: float = Field(ge=0, le=1e15)
    variable_opex_usd_per_year: float = Field(ge=0, le=1e15)
    feedstock_opex_usd_per_year: float = Field(ge=0, le=1e15)
    utility_opex_usd_per_year: float = Field(ge=0, le=1e15)
    production_units_per_year: float = Field(gt=0, le=1e15)
    selling_price_usd_per_unit: float = Field(ge=0, le=1e12)


def biosteam_project(snapshot: BioSTEAMSnapshot) -> dict:
    equipment = [
        QuotedEquipment(
            **u.model_dump(),
            reference_cepci=snapshot.reference_cepci,
            source=f"BioSTEAM {snapshot.library_version}: {snapshot.provenance}",
        ).model_dump()
        for u in snapshot.equipment
    ]
    return {
        "is_demo": False,
        "costing": {
            "equipment": equipment,
            "settings": {"cepci_current": snapshot.reference_cepci},
        },
        "financial": {
            "fixed_opex_usd_per_year": snapshot.fixed_opex_usd_per_year,
            "variable_opex_usd_per_year": snapshot.variable_opex_usd_per_year,
            "feedstock_opex_usd_per_year": snapshot.feedstock_opex_usd_per_year,
            "utility_opex_usd_per_year": snapshot.utility_opex_usd_per_year,
            "plant_capacity_units_per_year": snapshot.production_units_per_year,
            "product_selling_price_usd_per_unit": snapshot.selling_price_usd_per_unit,
        },
        "advisor_context": {
            "name": "BioSTEAM imported project",
            "classification": "biological",
            "description": snapshot.provenance,
        },
    }


def snapshot_biosteam(tea, product, *, reference_cepci: float, provenance: str) -> dict:
    """Call inside a trusted, already simulated BioSTEAM environment; product mass in kg/yr.

    The validated JSON is portable without coupling BioSTEAM/thermosteam dependencies to the API.
    Financial calculation is recomputed on FlowValue's disclosed basis, not asserted equal to BioSTEAM's TEA.
    """
    return BioSTEAMSnapshot(
        schema_version="flowvalue-biosteam-v1",
        library_version=version("biosteam"),
        reference_cepci=reference_cepci,
        provenance=provenance,
        equipment=[
            ExternalUnit(
                unit_id=u.ID,
                purchased_cost_usd=u.purchase_cost,
                installed_cost_usd=u.installed_cost,
            )
            for u in tea.system.units
            if u.purchase_cost > 0
        ],
        fixed_opex_usd_per_year=tea.FOC,
        variable_opex_usd_per_year=tea.VOC,
        feedstock_opex_usd_per_year=tea.material_cost,
        utility_opex_usd_per_year=tea.utility_cost,
        production_units_per_year=product.F_mass * tea.operating_days * 24,
        selling_price_usd_per_unit=product.price,
    ).model_dump()
