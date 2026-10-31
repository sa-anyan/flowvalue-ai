"""Keep a valid purchase component when installation/module alternatives conflict.

This adapter does not choose an installation method and does not change correlations.
The original strict registry call remains the default outside this explicit path.
"""

from dataclasses import replace

from . import registry
from .indexes.garrett.installation import InstallationBreakdown
from .indexes.garrett.integrated import list_factors


def estimate_component(curve_id, size, *, size_unit, source='garrett', **options):
    definitions = {f['id']: f for f in list_factors(curve_id)} if source == 'garrett' else {}
    requested = options.get('factors', [])
    kinds = {definitions.get(k, {}).get('kind') for k in requested}
    if not {'installation', 'module'} <= kinds:
        return registry.estimate_cost(curve_id, size, size_unit=size_unit, source=source, **options)
    purchase_options = dict(options, factors=[k for k in requested if definitions.get(k, {}).get('kind') not in {'installation','module'}])
    result = registry.estimate_cost(curve_id, size, size_unit=size_unit, source=source, **purchase_options)
    if result.estimate is None or result.estimate.cost_scope != 'purchased_equipment':
        return result
    evidence = dict(result.evidence, deferred_scope_factors=requested,
                    scope_decision='Purchased component only. Conflicting installation/module alternatives were not applied; user review required.')
    installation = InstallationBreakdown(result.equipment_cost, None, None, None, 'needs_review', evidence)
    return replace(result, installation=installation, evidence=evidence, status='provisional',
                   issues=result.issues + ('Installation/module alternatives conflict: neither is applied; purchased cost retained and installation remains unresolved.',))
