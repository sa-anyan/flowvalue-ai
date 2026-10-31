"""Optional OpenPyTEA 3.2.1 NPV cross-check; no upstream source is copied.

Run in a development environment that already has MIT-licensed OpenPyTEA 3.2.1.
The installed method starts its array at end-of-year one. Align timing explicitly
by passing future cash flows only and adding the initial time-zero amount once.
"""

from decimal import Decimal
from importlib.metadata import version


def compare_npv(initial, future_cash, discount_rate):
    if version("openpytea") != "3.2.1":
        raise ValueError("This reference harness is reviewed for OpenPyTEA 3.2.1 only")
    import numpy as np
    from openpytea.plant import Plant

    from ..investment_metrics.npv.calculator import npv

    # Exercise only the reviewed metric, avoiding implicit Plant economic defaults.
    reference = Plant.__new__(Plant)
    reference.cash_flow = np.asarray([float(x) for x in future_cash])
    reference.interest_rate = float(discount_rate)
    external = Decimal(str(reference._npv())) + initial
    point = (initial,) + tuple(future_cash)
    ours = npv((Decimal(0),) * len(point), point, discount_rate, "discrete_end")
    return {
        "version": "3.2.1",
        "comparison": "NPV only, matching end-year-one future cash plus initial time-zero investment",
        "flowvalue_npv": str(ours),
        "openpytea_npv": str(external),
        "absolute_difference": str(abs(ours - external)),
        "source": "https://github.com/pbtamarona/OpenPyTEA",
        "license": "MIT; installed distribution licence inspected; no code vendored",
    }
