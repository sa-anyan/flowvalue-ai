"""Six deterministic equation families; no eval, parallelisation or escalation."""

import math
from ...models import positive

REQUIRED = {
    "offset power-law": ("a", "b", "n"),
    "log-log quadratic": ("K1", "K2", "K3"),
    "ln-ln quadratic": ("K1", "K2", "K3"),
    "power-sizing": ("c0", "s0", "f"),
    "exponential": ("a", "b"),
    "2-var power-law": ("a", "b", "n", "n2"),
}


def coefficients(row):
    form = row["form"].strip().lower()
    if form not in REQUIRED:
        raise ValueError("Unsupported equation family")
    c = {}
    for name in (*REQUIRED[form], *(("K4", "K5") if "quadratic" in form else ())):
        raw = row.get(name, "")
        if raw == "" and name in {"K4", "K5"}:
            raw = 0  # source explicitly defines optional polynomial terms as zero
        if isinstance(raw, bool):
            raise ValueError("Invalid coefficient " + name)
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError("Nonfinite coefficient " + name)
        c[name] = value
    if form == "power-sizing" and (c["s0"] <= 0 or c["c0"] <= 0):
        raise ValueError("Scaling reference size and price must be positive")
    return form, c


def evaluate(
    row, size, second_size=None, *, enforce_bounds=True, allow_missing_bounds=False
):
    size = positive(size, "size")
    form, c = coefficients(row)
    for name, value, lo, hi in [
        ("size", size, "s_lower", "s_upper"),
        ("second_size", second_size, "s2_lower", "s2_upper"),
    ]:
        if name == "second_size" and form != "2-var power-law":
            continue
        value = positive(value, name)
        lower = float(row[lo]) if row.get(lo, "") != "" else None
        upper = float(row[hi]) if row.get(hi, "") != "" else None
        if enforce_bounds:
            if (lower is None or upper is None) and not allow_missing_bounds:
                raise ValueError(
                    "MODEL_APPLICABILITY_UNVERIFIED: published size bounds missing; explicit provisional acceptance required"
                )
            if (lower is not None and value < lower) or (
                upper is not None and value > upper
            ):
                raise ValueError(
                    "MODEL_OUT_OF_RANGE: "
                    + name
                    + " outside published bounds; no automatic extrapolation or parallelisation"
                )
    try:
        if form == "offset power-law":
            cost = c["a"] + c["b"] * size ** c["n"]
        elif form in {"log-log quadratic", "ln-ln quadratic"}:
            x = math.log10(size) if form == "log-log quadratic" else math.log(size)
            exponent = sum(c["K" + str(i + 1)] * x**i for i in range(5))
            cost = 10.0**exponent if form == "log-log quadratic" else math.exp(exponent)
        elif form == "power-sizing":
            cost = c["c0"] * (size / c["s0"]) ** c["f"]
        elif form == "exponential":
            cost = c["a"] * math.exp(c["b"] * size)
        else:
            cost = c["a"] + c["b"] * size ** c["n"] * second_size ** c["n2"]
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Nonfinite correlation output") from exc
    return positive(cost, "correlation cost")
