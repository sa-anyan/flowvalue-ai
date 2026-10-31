"""Reuse the sole financial engine for scenario edits; no separate scenario engine."""

from ...engine import calculate_financials
from ...snapshots import revise_inputs


def recalculate_scenario(baseline, *, actor, reason, expected_snapshot_id, **changes):
    scenario = revise_inputs(
        baseline,
        actor=actor,
        reason=reason,
        expected_snapshot_id=expected_snapshot_id,
        **changes,
    )
    return scenario, calculate_financials(scenario)
