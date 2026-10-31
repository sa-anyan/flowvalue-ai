"""Installation decomposition from configuration-specific Garrett source factors."""

import copy
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ...models import positive


@lru_cache(maxsize=1)
def _policies():
    return json.loads(
        Path(__file__)
        .with_name("data")
        .joinpath("installation_policies.json")
        .read_text()
    )


def installation_policy(curve_id):
    return copy.deepcopy(_policies()[curve_id])


@dataclass(frozen=True)
class InstallationBreakdown:
    equipment_cost: float | None
    installation_cost: float | None
    equipment_and_installation_cost: float | None
    installation_factor: float | None
    status: str
    evidence: dict


def calculate_installation(
    curve_id,
    purchase_amount,
    *,
    source_scope,
    variant=None,
    material_target=None,
    explicit_factor=None,
    index_multiplier=1.0,
):
    """Factor is total installed / purchase, not installation-only / purchase.

    The result retains the source per-unit basis. Physical quantities are applied
    by total_cost after scope/quantity validation, never guessed here.
    """
    policy = installation_policy(curve_id)
    amount = positive(purchase_amount, "equipment price basis")
    index_multiplier = positive(index_multiplier, "index multiplier")
    evidence = {
        "policy": policy,
        "historical_price_basis": amount,
        "index_multiplier": index_multiplier,
    }
    status = policy["status"]
    if status == "already_installed" or source_scope.startswith("installed"):
        evidence["reason"] = (
            "Installation is already included, but the source supplies no component split."
        )
        return InstallationBreakdown(
            None,
            None,
            positive(amount * index_multiplier, "indexed installed cost"),
            None,
            "already_included_unsplit",
            evidence,
        )
    if status == "scope_unresolved" or source_scope == "building_cost":
        return InstallationBreakdown(
            None, None, None, None, "scope_unresolved", evidence
        )
    factor = policy["default"]
    if variant is not None:
        if variant not in policy["choices"]:
            raise ValueError("Unknown installation_variant for selected configuration")
        factor = policy["choices"][variant]
    # Plate/frame construction-specific installation factors; do not borrow the
    # stainless factor for nickel/titanium or another construction.
    if (
        curve_id == "G287-092"
        and variant == "mild_steel"
        and material_target != "mild_steel"
    ):
        raise ValueError(
            "Mild-steel installation selection requires matching equipment material correction"
        )
    if curve_id == "G287-092" and material_target:
        if material_target == "mild_steel":
            factor = policy["choices"]["mild_steel"]
        elif "stainless" not in material_target:
            if explicit_factor is not None:
                raise ValueError(
                    "No installation factor is supplied for the modified material"
                )
            factor = None
            evidence["reason"] = (
                "Installation factor for modified plate/frame material is not supplied."
            )
    if explicit_factor is not None:
        allowed = [p for p in [policy["default"], *policy["choices"].values()] if p]
        match = next((p for p in allowed if p["id"] == explicit_factor["id"]), None)
        if match is None:
            raise ValueError(
                "Installation factor is not a source-supported choice for this curve"
            )
        if factor is not None and factor["id"] != match["id"]:
            raise ValueError(
                "Explicit installation factor conflicts with selected material/configuration"
            )
        factor = match
    equipment = positive(amount * index_multiplier, "indexed equipment cost")
    if factor is None:
        return InstallationBreakdown(
            equipment, None, None, None, "needs_review", evidence
        )
    f = positive(factor["multiplier"], "installation factor")
    if f < 1:
        raise ValueError("Installation factor must be at least one")
    installation = amount * (f - 1)
    combined = amount + installation
    # Currency/date escalation is identical for all three reconciled components.
    evidence.update(
        factor=factor,
        historical_equipment_cost=amount,
        historical_installation_cost=installation,
        historical_equipment_and_installation_cost=combined,
        calculation="installation = equipment * (factor - 1); combined = equipment + installation",
    )
    return InstallationBreakdown(
        equipment,
        positive(installation * index_multiplier, "indexed installation cost")
        if installation
        else 0.0,
        positive(combined * index_multiplier, "indexed combined cost"),
        f,
        "source_factor_estimate",
        evidence,
    )
