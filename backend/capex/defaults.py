"""Instant, deterministic CAPEX settings when none were chosen (no AI).

The Garrett detailed method needs a process type, an equipment delivery
basis and a fraction for each additive factor. When the plan lacks them
(the user has not chosen and no AI proposal ran), Python fills only the
missing keys:

* process type from the extracted equipment: solids-handling equipment
  (dryers, centrifuges, crushers, conveyors, screens, cyclones) alongside
  fluid equipment gives "mixed", solids handling alone "solids", otherwise
  "fluids";
* delivery basis "delivered" (catalogue purchase costs are treated as
  delivered equipment; stated, reviewable);
* factors at the midpoint of their published ranges (the engine's
  "midpoint" mode, Garrett Table 3-4), with offsite facilities at 0 until the
  user confirms they are not counted twice.

Every default is recorded with its basis so the user can review it; a value
the user or the AI already set is never replaced.
"""


SOLIDS_FAMILIES = {"dryer", "centrifuge", "crusher", "conveyor", "screen", "cyclone"}
FLUID_FAMILIES = {"pump", "compressor", "heat_exchanger", "tank", "vessel", "reactor", "column",
                  "electrolyser", "evaporator", "ion_exchange", "reverse_osmosis", "membrane",
                  "mixer", "settler", "boiler", "ph_adjustment"}
VERSION = "capex-python-defaults-1"


def process_type(report):
    """'solids', 'mixed' or 'fluids' from the equipment families in the register."""
    from backend.equipment_matching.deterministic import classify
    from backend.equipment_matching.service import equipment_register

    families = {classify(row).get("family") for row in equipment_register(report)}
    solids, fluids = families & SOLIDS_FAMILIES, families & FLUID_FAMILIES
    if solids and fluids:
        return "mixed", sorted(solids)
    if solids:
        return "solids", sorted(solids)
    return "fluids", []


def fill_missing(capex, report):
    """Return (capex settings with missing keys filled, [defaults applied])."""
    capex = dict(capex or {})
    applied = []
    capex.setdefault("model_id", "garrett")
    if capex["model_id"] != "garrett":
        return capex, applied
    if not capex.get("process_type"):
        kind, solids = process_type(report)
        capex["process_type"] = kind
        applied.append({"setting": "process_type", "value": kind,
                        "basis": ("solids-handling equipment present: " + ", ".join(solids)) if solids
                        else "no solids-handling equipment in the register"})
    if not capex.get("delivery_basis"):
        capex["delivery_basis"] = "delivered"
        applied.append({"setting": "delivery_basis", "value": "delivered",
                        "basis": "catalogue purchase costs treated as delivered equipment"})
    # Only when no factor choice exists: use the engine's own "midpoint" mode
    # (each factor recorded as a range-midpoint assumption). Offsite facilities
    # stay at 0: including them needs the user's confirmation that utilities and
    # buildings are not counted twice.
    if not capex.get("selected_factors") and not capex.get("factor_selection"):
        capex["factor_selection"] = "midpoint"
        capex["selected_factors"] = {"offsite_facilities": 0.0}
        applied.append({"setting": "factor_selection", "value": "midpoint",
                        "basis": "midpoint of each published Garrett range (Table 3-4); offsite facilities 0 until you confirm them"})
    if applied:
        capex.setdefault("working_capital", {"method": "model_default",
                                             "rationale": "Garrett documented default; provisional planning basis"})
    return capex, applied
