"""Current-price views never rewrite a saved source or call an AI provider."""
from unittest.mock import patch
from backend.orchestration.current_prices import _legacy_current_price_view_for_reference as current_price_view, _calculate


def test_current_view_recalculates_once_and_preserves_inputs():
    _calculate.cache_clear()
    saved = {'plan': {'equipment': []}, 'parsed': {'report': {'entities': []}}, 'results': {'old': True}, 'description': 'Test'}
    with patch('backend.orchestration.current_prices.run', return_value={'stages': {'capex': {'result': {'period': '2026-09'}}}}) as engine:
        view = current_price_view(saved)
        view['results']['changed'] = True
        again = current_price_view(saved)
        assert engine.call_count == 1
        assert engine.call_args.args[2]['cost_translation']['target_period'] == '2026-09'
        assert 'changed' not in again['results']
    assert saved['results'] == {'old': True}
    assert 'cost_translation' not in saved['plan']
    assert view['price_view']['status'] == 'recalculated'


def test_explicit_historical_policy_is_respected():
    saved = {'plan': {'cost_translation': {'enabled': False}}, 'results': {'old': True}}
    assert current_price_view(saved)['results'] == saved['results']
    assert current_price_view(saved)['price_view']['status'] == 'historical'


def test_missing_report_and_running_studies_are_not_fabricated():
    saved = {'plan': {}, 'results': {'old': True}}
    assert current_price_view(saved)['price_view']['status'] == 'unavailable'
    saved['running'] = True
    assert current_price_view(saved) == saved
