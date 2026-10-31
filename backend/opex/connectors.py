"""Inactive adapters: no engine calls, saves, routes or price escalation."""

import json
from decimal import localcontext

from backend.capex.models import CapexResult

from .indexes.garrett.model import PLANT_BASE
from .models import Basis, MoneyBase, OpexInputs


def prepare_opex_inputs(
    capex_result,
    *,
    assumptions=(),
    annual_revenue=None,
    revenue_source="",
    engineering_context=None,
    **options,
):
    """Map named canonical capital components, never total CAPEX or bare module.

    Capital and annual prices must already be aligned to the stated currency and
    price period. CEPCI is not a utility/salary/commodity escalation index.
    The source-specific Garrett base includes startup and offsite facilities.
    """
    if not isinstance(capex_result, CapexResult):
        raise TypeError("capex_result must be canonical CapexResult")
    if capex_result.issues or any(
        v is None
        for v in (
            capex_result.fixed_capital,
            capex_result.startup_expenses,
            capex_result.purchased_equipment,
            capex_result.currency,
            capex_result.period,
        )
    ):
        raise ValueError(
            "Canonical CAPEX is incomplete; cannot prepare reliable OPEX bases"
        )
    basis = Basis(capex_result.currency, capex_result.period)
    source = (
        "Canonical CAPEX model "
        + capex_result.model_id
        + "; fixed capital includes offsite; startup added; working capital excluded"
    )
    with localcontext() as context:
        context.prec = 40
        plant_base = capex_result.fixed_capital + capex_result.startup_expenses
    bases = [
        MoneyBase("fixed_capital", capex_result.fixed_capital, basis, source),
        MoneyBase(
            "purchased_equipment", capex_result.purchased_equipment, basis, source
        ),
        MoneyBase(PLANT_BASE, plant_base, basis, source),
    ]
    if annual_revenue is not None:
        bases.append(MoneyBase("annual_revenue", annual_revenue, basis, revenue_source))
    return OpexInputs(
        basis,
        assumptions=assumptions,
        bases=tuple(bases),
        engineering_context_json=json.dumps(
            engineering_context or {}, sort_keys=True, allow_nan=False
        ),
        **options,
    )


def financial_handoff(result):
    """Explicit separated outputs only. Caller must avoid depreciating twice."""
    if result.issues or result.annual_cash_opex is None:
        raise ValueError("Unresolved OPEX cannot feed financial calculations")
    return {
        "currency": result.basis.currency,
        "price_period": result.basis.price_period,
        "annual_fixed_cash_opex": result.cash_fixed,
        "annual_variable_cash_opex": result.cash_variable,
        "annual_cash_opex": result.annual_cash_opex,
        "annual_depreciation_separate": result.depreciation,
        "annual_financing_separate": result.financing,
        "opex_snapshot_id": result.snapshot_id,
        "basis": "One operating-year scenario, not a multiyear depreciation or loan schedule",
    }
