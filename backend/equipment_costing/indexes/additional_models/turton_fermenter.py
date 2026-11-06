"""Turton Table A.1 / OpenPyTEA parameter row; purchased cost, 2001 USD."""

from math import log10
from ...models import positive

K1, K2, K3 = 4.1052, 0.532, -0.0005


def calculate(volume_m3):
    v = positive(volume_m3, "fermenter design volume m3")
    if not 0.1 <= v <= 35:
        raise ValueError(
            "MODEL_OUT_OF_RANGE: fermenter requires 0.1–35 m3 per vessel. Review a sourced larger-scale model or independently designed modular configuration; never clamp/extrapolate automatically"
        )
    x = log10(v)
    return 10 ** (K1 + K2 * x + K3 * x * x)
