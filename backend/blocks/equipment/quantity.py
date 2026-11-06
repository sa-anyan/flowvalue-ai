"""Founder convention: a combined numbered AB tag represents two equal units.

This is a purchasing-count convention, not proof of duty/standby operation or
flow sharing. Explicit scenario quantities take precedence. Individual A or B
assets and tags without a numeric equipment stem are not expanded.
"""

import re


def equipment_quantity(proposal, tag):
    if "quantity" in proposal:
        return proposal["quantity"], "explicit_scenario_quantity"
    if re.search(r"\d\s*A\s*/?\s*B\s*$", str(tag), re.I):
        return 2, "founder_AB_pair_convention"
    return 1, "single_equipment_default"
