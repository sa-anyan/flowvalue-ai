"""Discover in-domain alternatives for review, never infer design equivalence.

Only supplied conceptual candidates are considered. The physical recipe and its
inputs are held fixed; prices are not used for candidate ranking. This is called
only during explicit AI equipment preparation, never deterministic recalculation
or Monte Carlo. Unknown contracts/scopes fail closed to the existing estimate.
"""
import copy
import math

from .unit_conversion.bridges.service import describe, evaluate, model_contract


def below_floor(line):
    estimate = getattr(getattr(line, 'calculation', None), 'estimate', None)
    return bool(estimate and any('BELOW-RANGE FLOOR' in str(note) for note in estimate.notes))


def _within(value, limits):
    try:
        low, high = map(float, limits)
        return math.isfinite(float(value)) and math.isfinite(low) and math.isfinite(high) and low <= float(value) <= high
    except (TypeError, ValueError, OverflowError):
        return False


def candidates(report, key, row):
    """Return stable, same-library/category/scope, in-range review candidates.

    Same category and coordinate do NOT prove suitability. The existing bounded
    specialist must still review configuration, service, material and pressure.
    An in-range candidate always precedes floor alternatives. If none exists,
    only strictly closer minimum-size floors may be reviewed. Multi-coordinate
    models must satisfy the secondary interval; no upper-range extrapolation.
    """
    spec = row.get('unit_conversion') or {}
    try:
        current, required, _ = model_contract(row.get('curve_id'))
        if not current.get('category') or not current.get('cost_scope'):
            return []
        current_preview = evaluate(report, key, spec)
    except (ValueError, TypeError, KeyError, OverflowError):
        return []
    ids = set((row.get('matching') or {}).get('candidate_model_ids', []))
    ids.update(row.get('candidate_curve_ids') or [])
    found, closer_floors = [], []
    current_size = current_preview['size']
    try:
        current_gap = float(current['capacity_limits'][0]) / current_size
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        current_gap = 1
    for model_id in sorted(ids):
        if model_id == row.get('curve_id'):
            continue
        try:
            model, requirement, _ = model_contract(model_id)
            if (model.get('source') != current.get('source')
                    or model.get('category') != current.get('category')
                    or model.get('cost_scope') != current.get('cost_scope')
                    or requirement.get('quantity') != required.get('quantity')
                    or (requirement.get('role') != required.get('role')
                        and required.get('quantity') not in {'volume', 'area', 'mass'})):
                continue
            context = describe(report, key, model_id)
            if context.get('issue') or spec.get('method') not in {r['id'] for r in context['recipes']}:
                continue
            trial = evaluate(report, key, {**copy.deepcopy(spec), 'model_id': model_id})
            inside = _within(trial['size'], model.get('capacity_limits'))
            gap = None
            if not inside:
                try:
                    low, high = map(float, model['capacity_limits'])
                    size = float(trial['size'])
                    gap = low / size
                    if not (math.isfinite(gap) and 0 < size < low <= high and 1 < gap < current_gap):
                        continue
                except (TypeError, KeyError, ValueError, ZeroDivisionError, OverflowError):
                    continue
            if trial.get('second_size') is not None and not _within(trial['second_size'], model.get('secondary_capacity_limits')):
                continue
            if inside:
                found.append(model_id)
            else:
                closer_floors.append((gap, model_id))
        except (ValueError, TypeError, KeyError, OverflowError):
            continue
    return found or [model_id for _, model_id in sorted(closer_floors)]
