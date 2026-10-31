"""PIPE PIPELINES — GARRETT P. 294 / PDF P. 44

Printed exponents only; documented comparable reference price required.
Mild steel pipeline, installed cost per foot; target is pipe size in inches, not pipeline length. Bare pipe, slurry and submarine curves have no separately specified exponents and remain unsupported.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {"pipeline": (0.99, "in_pipe_size", "installed_pipeline_unit_price_per_ft")}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported pipe_pipelines variant; no exponent will be invented"
        )
    exponent, unit, scope = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="pipe_pipelines",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        scope=scope,
        printed_page=294,
        notes=(
            "Mild steel pipeline, installed cost per foot; target is pipe size in inches, not pipeline length. Bare pipe, slurry and submarine curves have no separately specified exponents and remain unsupported.",
        ),
    )
