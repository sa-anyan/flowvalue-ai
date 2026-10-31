"""Typed six-category interpretation shared by the existing bounded LLM proposal.

No provider calls on edit/recalculation. External research uses the existing explicit
consent endpoint, never this prompt. A proposed opportunity is not a signed contract.
"""

from ..advisor import TEXT, obj
from ..validation import CATEGORIES

PROMPT = """Identify ALL distinct commercial payments in the process description.
Use product_sales for physical products only; processing_services for wastewater/
waste treatment and toll manufacturing; capacity_availability for reservations;
infrastructure_usage for access/throughput tariffs; environmental_attributes for
eligible credits/certificates; other_contractual_income for subsidies/bonuses/licensing.
Projects can use any combination. Do NOT put treatment fees in product sales.
Keep legacy sales only for physical products; use commercial_lines for all other
payments and optionally physical product net-price lines, never both for one payment.
Each distinct payment has one unique payment_id. Fixed and variable components can
be combined only if distinct contract scope is explicit. Minimum payment is a floor,
not an extra charge. Quantities/rates have explicit billing unit and monthly/annual
period. Each year's base rate is escalated from operating year 1; do not also inflate
annual rates already escalated. Use explicit year arrays across the entire life.
Link measured billable quantities to real M&E stream/property IDs. If quantity is
contractual or assumed, label it: never claim it came from the workbook. Unknown
applicable prices/quantities stay null and require questions; never make them silently zero.
For clauses explicitly not part of this scenario, specify neutral values and explain
that choice in rationale: fixed_payment=0 for variable-only payments; quantity=0 and
rate=0 for fixed-only payments; minimum_quantity=0 and minimum_payment=0 when no
minimum commitment is assumed; availability=1 when no availability deduction is
assumed; escalation=0 for a flat-price assumption. These are disclosed scenario
choices, not facts about an unseen contract. A fixed-only line uses quantity_unit
'payment' and rate_period 'per_unit'; fixed_payment holds the annual currency amount.
Billing quantity units are kg, m3, kWh, credit, payment or a comparable quantity,
never a price unit such as GBP/year. Do not calculate yearly billable quantities
from stream flow: put quantity=null when stream_key supplies it; Python calculates it.
User_confirmed requires an EXACT context_quote. User_assumption and llm_proposed
are separate from verified contracts. LLM proposals remain provisional even if used
in a conditional calculation. Eligibility/ownership for environmental attributes must
be explicit; no automatic policy compliance. Garrett's market/specification, demand,
competition, penetration and net-price guidance still applies. Do not invent sources,
quotes or contracts. No external research without separate user consent. No numerical
contract probability. Economic savings go in avoided_costs and identify one existing
OPEX input id (feed:..., energy:..., staff:..., other:...), never revenue; do not repeat
savings already reflected in lower prices/consumption or another payment. Savings
must be supported by an explicit counterfactual, not assumed from mere recovery.
"""


def schema():
    number = {"type": ["number", "null"], "minimum": 0}
    year = obj(
        {
            "year": {"type": "integer", "minimum": 1, "maximum": 50},
            "quantity": number,
            "rate": number,
            "fixed_payment": number,
            "minimum_quantity": number,
            "minimum_payment": number,
            "availability": number,
            "escalation": {"type": ["number", "null"]},
            "periods": {"type": "integer", "enum": [1, 12]},
        }
    )
    line = obj(
        {
            "id": TEXT,
            "name": TEXT,
            "category": {"type": "string", "enum": list(CATEGORIES)},
            "payment_id": TEXT,
            "quantity_unit": TEXT,
            "rate_period": {
                "type": "string",
                "enum": ["per_unit", "annual", "monthly"],
            },
            "arrangement": {
                "type": "string",
                "enum": ["user_confirmed", "user_assumption", "llm_proposed"],
            },
            "context_quote": TEXT,
            "rationale": TEXT,
            "uncertainty": TEXT,
            "source_references": {"type": "array", "items": TEXT},
            "stream_key": {"type": ["string", "null"]},
            "property": {
                "type": "string",
                "enum": [
                    "mass_flow",
                    "volume_flow",
                    "component_mass_flow",
                    "component_volume_flow",
                    "contract_quantity",
                ],
            },
            "component": {"type": ["string", "null"]},
            "fixed_variable_distinct": {"type": "boolean"},
            "eligibility_basis": TEXT,
            "years": {"type": "array", "items": year},
        }
    )
    savings = obj(
        {
            "id": TEXT,
            "target_opex_id": TEXT,
            "rationale": TEXT,
            "uncertainty": TEXT,
            "already_applied": {"type": "boolean"},
            "years": {
                "type": "array",
                "items": obj(
                    {
                        "year": {"type": "integer", "minimum": 1, "maximum": 50},
                        "amount": number,
                    }
                ),
            },
        }
    )
    return {
        "commercial_lines": {"type": "array", "items": line},
        "avoided_costs": {"type": "array", "items": savings},
    }


def interpret(provider, context):
    """Explicit caller-owned LLM invocation; never imported by calculators."""
    from backend.orchestration.equipment_advisor import validate as validate_shape

    contract = obj(schema())
    response = provider.generate(instructions=PROMPT, context=context, schema=contract)
    validate_shape(response, contract)
    return response
