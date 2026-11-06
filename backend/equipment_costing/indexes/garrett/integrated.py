"""Canonical Garrett curve engine: PDF equations first, provisional graph fits second."""

import copy
import json
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

from ...cost_to_future.escalator import adjust_cost
from ...models import CostEstimate, positive
from . import (
    activated_carbon_adsorbers,
    coolers_quenchers,
    ducts,
    heat_exchangers_spiral_plate,
)
from .general import SOURCE_FILENAME, SOURCE_SHA256, SOURCE_TITLE, scale_cost
from .graph_models import fit_points
from .installation import (
    InstallationBreakdown,
    calculate_installation,
    installation_policy,
)
from .pressure_adjustment import adjust_pressure, list_pressure_methods

DATA = Path(__file__).with_name("data")


@lru_cache(maxsize=8)
def _read(name):
    data = json.loads((DATA / name).read_text())
    if name == "review_curves.json":
        corrections = json.loads((DATA / "source_corrections.json").read_text())
        for curve in data["curves"]:
            correction = corrections["models"].get(curve["id"])
            if not correction:continue
            curve["source_correction"] = {**correction,"source":corrections["source"]}
            curve["size_unit"] = "actual chamber volume, ft3"
            if "points" in correction:
                template=copy.deepcopy(curve["points"][0])
                curve["points"]=[{**template,"size":p["size"],"source_price":p["price"]/1000,"cached_usd":p["price"],"source_correction":correction["note"],"purpose":"Graph anchor (unverified)","status":"Pending","confidence":"Low","size_unit":curve["size_unit"]} for p in correction["points"]]
            else:
                for point in curve["points"]:
                    if point["size"] is not None:point["size"]*=correction["physical_volume_multiplier"]
                    point["size_unit"]=curve["size_unit"]
    return data


def list_models():
    """Return independent metadata snapshots; never expose mutable cached data."""
    models = copy.deepcopy(_read("review_curves.json")["curves"])
    for curve in models:
        interpretation = _read("interpretations.json")[curve["id"]]
        curve["interpretation"] = copy.deepcopy(interpretation)
        curve["installation_policy"] = installation_policy(curve["id"])
        curve["pressure_adjustment_options"] = list_pressure_methods(curve["id"])
        curve["available_factor_ids"] = [f["id"] for f in list_factors(curve["id"])]
        sizes = [p["size"] for p in curve["points"] if p["size"] is not None]
        curve["observed_size_range"] = [min(sizes), max(sizes)] if sizes else None
        curve["range_status"] = (
            "observed sample interval, not validated applicability range"
        )
    return models


def list_factors(curve_id):
    return copy.deepcopy(
        [f for f in _read("factors.json") if curve_id in f["allowed_curve_ids"]]
    )


@dataclass(frozen=True)
class CostingResult:
    status: str
    estimate: CostEstimate | None
    historical_amount: float | None
    issues: tuple[str, ...]
    evidence: dict
    fit_diagnostics: tuple[dict, ...] = ()
    applied_factors: tuple[dict, ...] = ()
    index_adjustment: dict | None = None

    installation: InstallationBreakdown | None = None

    @property
    def equipment_cost(self):
        return self.installation.equipment_cost if self.installation else None

    @property
    def installation_cost(self):
        return self.installation.installation_cost if self.installation else None

    @property
    def equipment_and_installation_cost(self):
        return (
            self.installation.equipment_and_installation_cost
            if self.installation
            else None
        )

    @property
    def amount(self):
        return self.estimate.amount if self.estimate else None


@lru_cache(maxsize=256)
def _curve(curve_id):
    for curve in _read("review_curves.json")["curves"]:
        if curve["id"] == curve_id:
            return curve
    raise ValueError(
        "Unknown Garrett curve ID; select an exact registered configuration"
    )


def _scope(curve):
    unit = curve["price_unit"].lower()
    if "per ft³" in unit:
        return "unit_price_per_ft3"
    if "per ft²" in unit:
        return (
            "installed_unit_price_per_ft2"
            if "installed" in unit
            else "unit_price_per_ft2"
        )
    if "per ft of column height" in unit:
        return "unit_price_per_ft_height"
    if "linear ft" in unit:
        return (
            "installed_unit_price_per_ft"
            if "installed" in unit
            else "pipe_unit_price_per_ft"
        )
    if "per tray" in unit:
        return "unit_price_per_tray"
    if curve["printed_page"] == 264:
        return "building_cost"
    return "purchased_equipment"


def _multiplier(curve):
    unit = curve["price_unit"].lower()
    if "usd" not in unit:
        raise ValueError("Unsupported price currency/unit")
    return 1000 if "thousands" in unit else 1


def _band(curve_id, size):
    if curve_id == "G257-002":
        return (
            ((0, 4), 0.23)
            if size < 4
            else (((4, 30), 0.56) if size <= 30 else ((30, float("inf")), 0.68))
        )
    if curve_id == "G257-003":
        return ((1, 3), 0.42) if size <= 3 else ((3, 100), 0.51)
    return None


@lru_cache(maxsize=512)
def _fit(curve_id, band_key):
    curve = _curve(curve_id)
    meta = _read("interpretations.json")[curve_id]
    points = curve["points"]
    exponent = meta["printed_exponent"]
    lower, upper = meta.get("source_range", (0, float("inf")))
    if band_key is not None:
        (lower, upper), exponent = band_key
    points = [p for p in points if p["size"] is None or lower <= p["size"] <= upper]
    # Bands that share an endpoint are never bridged. For turbine >30 HP,
    # exclude the 30 HP endpoint whose printed exponent is different.
    if curve_id == "G257-002" and upper == 4:
        points = [p for p in points if p["size"] is None or p["size"] < 4]
    if curve_id == "G257-002" and lower == 30:
        points = [p for p in points if p["size"] is None or p["size"] > 30]
    return fit_points(points, multiplier=_multiplier(curve), exponent=exponent)


def _direct(curve, size, extrapolation_exponent=None, extrapolation_justification=None):
    """Return authoritative equation method without fitting inaccurate graph data."""
    page = curve["printed_page"]
    sizes = [
        positive(p["size"], "graph size")
        for p in curve["points"]
        if p["size"] is not None
    ]
    if page == 256:
        return activated_carbon_adsorbers.estimate_cost(size * 1000)
    if page == 274 and curve["configuration"] in ("Quencher", "Spray chamber"):
        if not sizes:
            raise ValueError("Reviewed flow interval required")
        # No justified source cost exponent for affine equations outside sample interval.
        if not min(sizes) <= size <= max(sizes) and (
            extrapolation_exponent is None
            or not isinstance(extrapolation_justification, str)
            or not extrapolation_justification.strip()
        ):
            raise ValueError(
                "Unsupported extrapolation: affine spray/quencher equation has no validated sizing exponent outside the supplied interval"
            )
        return coolers_quenchers.estimate_cost(
            size,
            variant="quencher"
            if curve["configuration"] == "Quencher"
            else "spray_chamber",
            valid_flow_range=(min(sizes), max(sizes)),
            extrapolation_exponent=extrapolation_exponent
            if extrapolation_exponent is not None
            else 1.0,
        )
    if page == 278:
        return ducts.estimate_cost(
            size,
            variant="mild_steel"
            if curve["configuration"].startswith("Mild")
            else "stainless",
            valid_diameter_range=(min(sizes), max(sizes)),
        )
    if page == 287:
        return heat_exchangers_spiral_plate.estimate_cost(
            size,
            variant="spiral_plate"
            if curve["configuration"].startswith("Spiral")
            else "plate_and_frame",
            valid_area_range=(min(sizes), max(sizes)),
        )
    return None


def estimate_cost(
    curve_id,
    size,
    *,
    size_unit,
    allow_unverified=False,
    allow_fitted_extrapolation=True,
    factors=(),
    factor_basis_confirmation=None,
    extrapolation_exponent=None,
    extrapolation_justification=None,
    target_index=None,
    target_period=None,
    target_index_source=None,
    index_series="CEPCI",
    installation_variant=None,
    pressure_adjustment=None,
):
    """Exact source-coordinate units required. No fuzzy equipment/material matching.

    Provisional graph prices and factor transcriptions need allow_unverified=True.
    With provisional graph use enabled, graph-only models may use their fitted n
    and the nearest observed boundary price for explicitly flagged extrapolation.
    No generic exponent or reference price is invented. Set allow_fitted_extrapolation
    to False for the previous strict policy requiring a printed/caller-justified n.
    Explicit caller exponents always require a recorded justification.
    """
    curve = _curve(curve_id)
    size = positive(size, "size")
    if size_unit != curve["size_unit"]:
        raise ValueError(
            "Size unit must exactly match the selected model; no implicit conversion"
        )
    if type(allow_unverified) is not bool:
        raise ValueError("allow_unverified must be a boolean")
    if type(allow_fitted_extrapolation) is not bool:
        raise ValueError("allow_fitted_extrapolation must be a boolean")
    meta = _read("interpretations.json")[curve_id]
    source = _read("review_curves.json")
    evidence = {
        "curve_id": curve_id,
        "source_correction":curve.get("source_correction"),
        "configuration": curve["configuration"],
        "printed_page": curve["printed_page"],
        "pdf_page": curve["pdf_page"],
        "register_cells": curve["register_cell_range"],
        "workbook_filename": source["workbook_filename"],
        "workbook_sha256": source["workbook_sha256"],
        "pdf_filename": source["pdf_filename"],
        "pdf_sha256": source["pdf_sha256"],
        "size_input": size,
        "size_input_unit": size_unit,
        "source_range": meta.get("source_range"),
        "source_factor_review": f"pdf_review_notes.json:{curve['printed_page']}",
        "points": copy.deepcopy(curve["points"]),
    }
    issues = list(meta["warnings"])
    diagnostics = ()

    def blocked(message):
        return CostingResult("needs_review", None, None, (*issues, message), evidence)

    if meta["blocking_issues"]:
        return blocked("; ".join(meta["blocking_issues"]))
    try:
        base = _direct(curve, size, extrapolation_exponent, extrapolation_justification)
        if base is None:
            if not allow_unverified:
                return blocked(
                    "Unverified graph readings require explicit allow_unverified=True"
                )
            fit = _fit(curve_id, _band(curve_id, size))
            diagnostics = fit.diagnostics
            anchor = min(max(size, fit.lower), fit.upper)
            n = fit.exponent
            exponent_basis = fit.exponent_basis
            provisional_boundary = False
            extrapolated = size != anchor
            if extrapolated:
                if extrapolation_exponent is not None:
                    if (
                        not isinstance(extrapolation_justification, str)
                        or not extrapolation_justification.strip()
                    ):
                        return blocked(
                            "Caller extrapolation exponent requires a documented justification"
                        )
                    # scale_cost validates finiteness and permits negative packing exponents.
                    scale_cost(1, 1, 2, extrapolation_exponent)
                    n = extrapolation_exponent
                    issues.append(
                        "Caller-justified exponent: " + extrapolation_justification
                    )
                elif meta["printed_exponent"] is None and _band(curve_id, size) is None:
                    if not allow_fitted_extrapolation:
                        return blocked(
                            "Unsupported extrapolation: fitted graph exponent alone is not an engineering justification"
                        )
                    provisional_boundary = True
                    exponent_basis = "Provisional log-space fitted exponent from unverified graph points; not a printed Garrett exponent"
                    issues.append(
                        "PROVISIONAL BOUNDARY EXTRAPOLATION: fitted graph exponent is an estimation assumption, not validated engineering scaling"
                    )
                if extrapolation_exponent is not None:
                    exponent_basis = "Caller-supplied exponent: " + extrapolation_justification
            anchor_cost = fit.evaluate(anchor)
            if provisional_boundary:
                boundary_points = [p for p in curve["points"] if p.get("row") in fit.training_rows and p.get("size") == anchor and p.get("source_price") is not None]
                if not boundary_points:
                    return blocked("No usable observed boundary price for provisional extrapolation")
                point = boundary_points[0]
                anchor_cost = positive(point["source_price"], "boundary source price") * _multiplier(curve)
                evidence["boundary_reference"] = {"size": anchor, "cost": anchor_cost, "source_row": point["row"], "source_cells": point["cell_range"], "status": "unverified_graph_reading"}
            if extrapolated:
                evidence["extrapolation"] = {"formula": "C2 = C1 * (S2/S1)**n", "anchor_size": anchor, "anchor_cost": anchor_cost, "target_size": size, "size_ratio": size / anchor, "distance_factor": max(size / anchor, anchor / size), "exponent": n, "exponent_basis": exponent_basis, "provisional_fitted_exponent": provisional_boundary}
                if max(size / anchor, anchor / size) >= 10:
                    issues.append("VERY LARGE EXTRAPOLATION: target and boundary sizes differ by at least 10-fold; accuracy is unvalidated")
            amount = scale_cost(anchor_cost, anchor, size, n)
            issues.append(
                "UNVERIFIED graph estimate; fitted reference cost is not a supplier quotation"
            )
            if (
                curve["printed_page"] in [257, 265, 281, 291, 295, 299]
                or meta["printed_exponent"] is None
            ):
                issues.append(
                    "A power law is a provisional approximation; curvature/linear-axis plots may not follow one exponent"
                )
            if any(abs(d["residual_percent"]) > 20 for d in diagnostics):
                issues.append(
                    "Fit/source discrepancy exceeds 20% for at least one point; review diagnostics (not an accuracy bound)"
                )
            base = CostEstimate(
                equipment=curve["equipment"],
                variant=curve_id,
                amount=amount,
                currency="USD",
                cost_index=320,
                period="early 1987",
                size=size,
                size_unit=size_unit,
                cost_scope=_scope(curve),
                formula="C2 = C1 * (S2 / S1)**n; log-space fitted C1",
                printed_page=curve["printed_page"],
                pdf_page=curve["pdf_page"],
                source_title=SOURCE_TITLE,
                source_filename=SOURCE_FILENAME,
                source_sha256=SOURCE_SHA256,
                exponent=n,
                extrapolated=extrapolated,
                anchor_size=anchor if extrapolated else None,
                anchor_cost=anchor_cost if extrapolated else None,
                exponent_basis=exponent_basis,
                notes=tuple(issues),
            )
            evidence["fit"] = {
                "training_rows": fit.training_rows,
                "observed_range": [fit.lower, fit.upper],
                "fitted_anchor_size": fit.anchor_size,
                "fitted_anchor_cost": fit.anchor_cost,
                "fitted_exponent": fit.exponent,
            }
        else:
            evidence["method"] = "existing PDF direct equation"
            # Keep numerical graph/formula disagreements visible, without fitting
            # an authoritative formula to the unverified workbook readings.
            for point in curve["points"]:
                if (
                    point["size"] is None
                    or point["source_price"] is None
                    or curve["printed_page"] == 278
                ):
                    continue
                try:
                    predicted = _direct(curve, point["size"])
                    observed = point["source_price"] * _multiplier(curve)
                    diagnostics += (
                        {
                            "row": point["row"],
                            "cell_range": point["cell_range"],
                            "observed": observed,
                            "predicted": predicted.amount,
                            "residual_percent": (predicted.amount / observed - 1) * 100,
                        },
                    )
                except ValueError:
                    pass
            if any(abs(d["residual_percent"]) > 20 for d in diagnostics):
                issues.append(
                    "Workbook graph readings conflict with PDF equation by more than 20%; equation retained"
                )
        if base.extrapolated:
            issues.append(
                "EXTRAPOLATED from nearest usable boundary; accuracy unvalidated"
            )
        if pressure_adjustment is not None:
            available_factors = {f["id"]: f for f in list_factors(curve_id)}
            if any(
                available_factors.get(f, {}).get("kind") == "pressure" for f in factors
            ):
                return blocked(
                    "Choose either a relative pressure adjustment or a discrete pressure factor; do not stack them"
                )
            adjusted_amount, pressure_evidence = adjust_pressure(
                curve_id,
                base.amount,
                pressure_adjustment,
                allow_unverified=allow_unverified,
            )
            evidence["pressure_adjustment"] = pressure_evidence
            base = replace(
                base,
                amount=adjusted_amount,
                notes=base.notes + (pressure_evidence["warning"],),
            )
            issues.append(
                "Pressure adjustment is provisional: "
                + pressure_evidence["applicability"]
            )
        evidence["uncorrected_historical_amount"] = base.amount
        evidence["uncorrected_scope"] = base.cost_scope
        applied = []
        if factors:
            if not allow_unverified:
                return blocked(
                    "Source factor transcriptions require explicit provisional-data approval"
                )
            if (
                not isinstance(factor_basis_confirmation, str)
                or not factor_basis_confirmation.strip()
            ):
                return blocked(
                    "Factor applicability requires a documented baseline/configuration confirmation"
                )
            if len(set(factors)) != len(factors):
                raise ValueError("Duplicate correction factors")
            available = {f["id"]: f for f in list_factors(curve_id)}
            kinds = set()
            for identifier in factors:
                if identifier not in available:
                    raise ValueError(
                        "Unknown or inapplicable correction factor for this exact curve"
                    )
                factor = available[identifier]
                kind = factor["kind"]
                if kind in kinds:
                    raise ValueError(
                        "Only one factor per category; do not stack alternative configurations"
                    )
                kinds.add(kind)
                applied.append(factor)
            if "module" in kinds and "installation" in kinds:
                raise ValueError(
                    "Installation and module factors are alternative scopes, not cumulative multipliers"
                )
            if "installation" in kinds and base.cost_scope != "purchased_equipment":
                raise ValueError(
                    "Installation factor cannot multiply an already installed or unit-price scope"
                )
            if "module" in kinds and (
                "installed" in base.cost_scope
                or base.cost_scope != "purchased_equipment"
            ):
                raise ValueError(
                    "Module factor cannot multiply installed or unit-price scopes"
                )
            corrected = base.amount
            for factor in applied:
                corrected = positive(
                    corrected * positive(factor["multiplier"], "factor"),
                    "corrected cost",
                )
            base = replace(
                base,
                amount=corrected,
                cost_scope="module_estimate"
                if "module" in kinds
                else (
                    "installed_equipment"
                    if "installation" in kinds
                    else base.cost_scope
                ),
                notes=base.notes
                + (
                    "Applied scoped source factors with caller confirmation: "
                    + factor_basis_confirmation,
                ),
            )
            issues.append(
                "Correction-factor transcriptions and applicability remain provisional"
            )
        # Retain purchase basis independently of module/installation multipliers.
        # Material/pressure/design factors affect equipment price first.
        purchase_basis = evidence["uncorrected_historical_amount"]
        material_target = None
        explicit_installation = None
        for factor in applied:
            if factor["kind"] == "installation":
                explicit_installation = factor
            elif factor["kind"] != "module":
                purchase_basis *= factor["multiplier"]
                if factor["kind"] == "material":
                    material_target = factor["target_configuration"]
        historical = base.amount
        index_evidence = None
        if target_index is not None:
            adjusted = adjust_cost(
                base.amount,
                base_index=320,
                target_index=target_index,
                base_series="CEPCI",
                target_series=index_series,
                target_period=target_period,
                target_source=target_index_source,
            )
            index_evidence = {
                "base_index": 320,
                "target_index": target_index,
                "series": index_series,
                "target_period": target_period,
                "target_source": target_index_source,
                "multiplier": target_index / 320,
            }
            base = replace(
                base,
                amount=adjusted,
                cost_index=target_index,
                period=target_period,
                notes=base.notes
                + (
                    "Index ratio applied; currency unchanged. Historical corrected amount retained separately.",
                ),
            )
        installation = calculate_installation(
            curve_id,
            purchase_basis,
            source_scope=evidence["uncorrected_scope"],
            variant=installation_variant,
            material_target=material_target,
            explicit_factor=explicit_installation,
            index_multiplier=index_evidence["multiplier"] if index_evidence else 1.0,
        )
        evidence["installation"] = installation.evidence
        status = (
            "provisional"
            if any("UNVERIFIED" in i or "provisional" in i for i in issues) or applied
            else "formula_estimate"
        )
        return CostingResult(
            status,
            base,
            historical,
            tuple(issues),
            evidence,
            tuple(copy.deepcopy(diagnostics)),
            tuple(copy.deepcopy(applied)),
            index_evidence,
            installation,
        )
    except (ValueError, TypeError, OverflowError) as exc:
        return blocked(str(exc))
