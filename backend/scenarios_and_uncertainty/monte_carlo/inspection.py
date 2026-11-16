"""Reconstruct a draw from frozen inputs and saved samples, without recalculating."""
import copy
import hashlib
import json

from .discovery import get
from .models import Parameter
from .equipment_projection import equipment_records
from .scenarios import apply


def configuration_hash(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def inspect_run(result, index):
    if not 0 <= index < len(result['runs']):
        raise IndexError('Run not found')
    run = copy.deepcopy(result['runs'][index])
    plan = copy.deepcopy(result['effective_fixed_plan'])
    parameters = [Parameter.model_validate(p) for p in result['settings']['parameters']]
    enabled = [p for p in parameters if p.enabled]
    apply(plan, enabled, [run['samples'][p.id] for p in enabled])
    digest = configuration_hash(plan)
    if run.get('configuration_hash') and run['configuration_hash'] != digest:
        raise ValueError('Saved configuration fingerprint does not reconcile; do not use this run in a report')
    original = result.get('baseline_plan') or {}
    def value(source, target):
        try:
            return copy.deepcopy(get(source, target))
        except (KeyError, IndexError, TypeError):
            return None
    run['configuration'] = {
        'hash': digest, 'fingerprint_verified': bool(run.get('configuration_hash')),
        'baseline_id': result['baseline_id'], 'baseline_revision': result['baseline_revision'],
        'snapshot_id': result.get('audit', {}).get('frozen_snapshot_id'),
        'calculation_source_hash': result.get('audit', {}).get('calculation_source_hash'),
        'seed': result['settings']['seed'], 'study_settings': result['settings'],
        'plan': plan, 'source_report': result.get('source_report'),
        'process_description': result.get('process_description'),
        'parameters': [{**p.model_dump(), 'values': [
            {'target': target, 'baseline': value(original, target), 'applied': value(plan, target)}
            for target in p.targets]} for p in parameters],
        'notice': 'Exact frozen inputs for this draw. Non-selected inputs remain fixed. Reconstruction does not rerun calculations or change the baseline.',
    }
    return run


def run_index(result):
    return [{'index': r['index'], 'status': r['status'], 'metrics': r.get('metrics', {}),
             'samples': r.get('samples', {}), 'coverage': r.get('coverage'),
             'equipment_costs': {e['record_key']: e['cost'] for e in equipment_records(r) if e['price_coverage'] == 'priced'},
             'reason': r.get('reason'),
             'metric_eligible': [k for k, v in r.get('metrics', {}).items() if v is not None and (r['status'] == 'complete' if k in {'npv', 'irr', 'payback'} else r['status'] != 'failed' and not r.get('invalid_calculations'))],
             'configuration_hash': r.get('configuration_hash')}
            for r in result['runs']]


def inspect_calculations(result, index):
    """Saved stage evidence, or a verified canonical replay for older studies.

    Replay is read-only. Never substitute newly calculated amounts if the saved
    draw cannot be reproduced by the currently installed engines.
    """
    inspected = inspect_run(result, index)
    if inspected.get('calculation_trace'):
        inspected['trace_verification'] = {'status': 'saved', 'notice': 'Calculation rows saved with this variation.'}
        return inspected
    if not result.get('source_report') or inspected.get('status') == 'failed':
        inspected['trace_verification'] = {'status': 'unavailable', 'notice': 'This historical variation has no saved calculation rows or replayable source.'}
        return inspected
    from .engine import evaluate
    aliases = [a['equipment_key'] for a in result['settings'].get('aliases', [])]
    config = inspected['configuration']
    try:
        replay = evaluate(config['source_report'], config['process_description'], copy.deepcopy(config['plan']), aliases)
        fields = ('metrics', 'cash_flow', 'equipment_records', 'capex_components', 'opex_components')
        if any(replay.get(key) != inspected.get(key) for key in fields):
            inspected['trace_verification'] = {'status': 'mismatch', 'notice': 'The current engines do not reproduce this saved variation. New breakdowns are withheld; saved totals and inputs remain available.'}
        else:
            inspected['calculation_trace'] = replay['calculation_trace']
            inspected['trace_verification'] = {'status': 'replayed', 'notice': 'Reconstructed from frozen inputs. Equipment costs, CAPEX and OPEX lines, headline results and cash flow match the saved variation exactly. The original study and baseline are unchanged.'}
    except (ValueError, TypeError, KeyError, ArithmeticError, AttributeError):
        inspected['trace_verification'] = {'status': 'unavailable', 'notice': 'Calculation rows could not be reproduced. Saved totals and configuration remain available.'}
    return inspected
