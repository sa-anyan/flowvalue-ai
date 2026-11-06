"""EPA Equation 3-16: unit-package capital, 1989 USD; natural logarithms."""

from math import exp, log
from ...models import positive


def calculate(flow_us_mgd):
    q = positive(flow_us_mgd, "US MGD")
    if not 0.00001 <= q <= 5:
        raise ValueError(
            "MODEL_OUT_OF_RANGE: outside EPA Table 3-22 tabulated evaluation interval 0.00001–5 US MGD; no extrapolation"
        )
    x = log(q)
    return exp(11.721 + 0.543 * x + 0.000139 * x * x)
