"""Metadata and deterministic adapter for additional published models.

No upstream software execution, built-in currency conversion, or installation uplift.
"""

from dataclasses import asdict
from ...models import CostEstimate
from ..garrett.integrated import CostingResult
from ..garrett.installation import InstallationBreakdown
from . import epa_ph_adjustment, turton_fermenter, watertap_clarifier

EPA = "epa_ph_adjustment_1989"
TURTON = "fermenter_reactor_turton_2001"
CIRCULAR = "watertap_circular_clarifier_2011"
RECTANGULAR = "watertap_rectangular_clarifier_2011"


def list_models():
    rows = [
        dict(
            id=EPA,
            category="Wastewater pH adjustment system",
            configuration="Continuous neutralisation package",
            aliases=[
                "pH adjustment",
                "neutralization",
                "neutralisation",
                "acid dosing",
            ],
            size_unit="US_MGD",
            quantity="volume_flow",
            source_year="1989",
            cost_scope="unit_capital",
            capacity_limits=[0.00001, 5],
            range_status="Table 3-22 tabulated evaluation interval, not a certified applicability range",
            reference="US EPA EPA-821-R-95-002, January 1995, Equation 3-16, pp. 3-30–3-32",
            source_url="https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=200031RR.TXT",
            source_page=30,
            included_categories=[
                "installation",
                "piping",
                "instrumentation",
                "engineering",
                "contingency",
            ],
            scope_note="One tank, agitator and sulfuric-acid feed system; five-minute detention source design basis. Upstream rapid mixing/clarification and operating chemicals are separate.",
        ),
        dict(
            id=TURTON,
            category="Fermenter / fungal bioreactor",
            configuration="Carbon steel, ambient pressure, purchased vessel",
            aliases=["fermenter", "fermentation reactor", "fungal bioreactor"],
            size_unit="m3",
            quantity="volume",
            source_year="2001",
            cost_scope="purchased_equipment",
            capacity_limits=[0.1, 35],
            range_status="Published correlation range; no automatic extrapolation",
            reference="Turton et al., Analysis, Synthesis, and Design of Chemical Processes, Table A.1; OpenPyTEA correlation dataset",
            source_url="https://openpytea.readthedocs.io/en/latest/user_guide/cost_correlations.html",
            source_page=0,
            included_categories=[],
            scope_note="Base purchased cost, carbon steel, ambient pressure. Auxiliary/agitation/aeration scope not itemised in verified dataset: review separately, do not presume inclusion or exclusion.",
        ),
    ]
    for geometry, identifier in [("circular", CIRCULAR), ("rectangular", RECTANGULAR)]:
        rows.append(
            dict(
                id=identifier,
                category="Mechanically equipped clarifier",
                configuration=geometry,
                aliases=[geometry + " clarifier", "biomass settler", "clarification"],
                size_unit="ft2",
                quantity="area",
                source_year="2011",
                cost_scope="unit_capital",
                capacity_limits=None,
                range_status="Published capacity range unverified; positive, increasing polynomial domain is only a mathematical guard",
                reference="Sharma, Najafi and Qasim (2013), Journal of Infrastructure Systems 19(4), 451–464; WaterTAP 1.8.0 clarifier costing",
                source_url="https://watertap.readthedocs.io/en/1.8.0/technical_reference/costing/clarifier.html",
                source_page=0,
                included_categories=[],
                scope_note="Native construction/capital polynomial only; WaterTAP TIC factor and currency escalation not applied. Auxiliary scope not itemised; not a simple settling vessel model.",
            )
        )
    equations = {
        EPA: {"log_base": "natural", "coefficients": [11.721, 0.543, 0.000139]},
        TURTON: {"log_base": 10, "coefficients": [4.1052, 0.532, -0.0005]},
        CIRCULAR: {"polynomial_coefficients": [-0.0006, 98.952, 191806]},
        RECTANGULAR: {"polynomial_coefficients": [-0.0029, 169.19, 94365]},
    }
    for m in rows:
        m["equation_parameters"] = equations[m["id"]]
        m["included_auxiliaries"] = (
            ["one tank", "one agitator", "one sulfuric acid feed system"]
            if m["id"] == EPA
            else []
        )
        m["excluded_auxiliaries"] = (
            ["upstream rapid mixing", "clarification", "chemical operating costs"]
            if m["id"] == EPA
            else []
        )
        m["unresolved_auxiliary_scope"] = m["id"] != EPA
        m.update(
            source="additional_models",
            currency="USD",
            input_requirements=[
                dict(quantity=m.pop("quantity"), unit=m["size_unit"], required=True)
            ],
            limitation=m["scope_note"] + " " + m["range_status"],
            escalation="Canonical dated same-currency indices; explicit provisional inflation proxy or missing-index requirement",
            confidence="source_equation; project applicability requires engineering review",
        )
    return rows


def estimate_cost(model_id, size, *, size_unit, input_provenance=None, **options):
    from ...unit_conversion import convert

    models = {m["id"]: m for m in list_models()}
    if model_id not in models:
        raise ValueError("Unknown additional model")
    allowed = {"allow_unverified", "unit_context"}
    unknown = {k for k, v in options.items() if v is not None and v != []} - allowed
    if unknown:
        raise ValueError(
            "Unsupported additional-model corrections: "
            + ", ".join(sorted(unknown))
            + "; no generic installation/material/pressure factors"
        )
    m = models[model_id]
    converted = convert(
        size,
        size_unit,
        m["size_unit"],
        context=options.get("unit_context"),
        source=input_provenance or {},
    )
    if converted.value is None:
        raise ValueError("; ".join(converted.issues))
    value = converted.value
    if model_id == EPA:
        amount = epa_ph_adjustment.calculate(value)
        equation = "exp(11.721 + 0.543*ln(Q) + 0.000139*ln(Q)**2)"
    elif model_id == TURTON:
        amount = turton_fermenter.calculate(value)
        equation = "10**(4.1052 + 0.532*log10(V) - 0.0005*log10(V)**2)"
    else:
        amount = watertap_clarifier.calculate(
            value,
            m["configuration"],
            allow_unverified=options.get("allow_unverified", False),
        )
        equation = (
            str(watertap_clarifier.COEFFICIENTS[m["configuration"]])
            + " polynomial in area ft2"
        )
    issues = (m["scope_note"], m["range_status"])
    estimate = CostEstimate(
        m["category"],
        m["configuration"],
        amount,
        "USD",
        1.0,
        m["source_year"],
        value,
        m["size_unit"],
        m["cost_scope"],
        equation,
        m["source_page"],
        0,
        m["reference"],
        m["source_url"],
        "",
        notes=issues,
        index_series="SOURCE_PRICE_BASIS",
    )
    evidence = dict(
        source="additional_models",
        model_id=model_id,
        model_metadata=m,
        source_reference=m["reference"],
        source_url=m["source_url"],
        original_cost=amount,
        original_cost_year=m["source_year"],
        unit_conversion=asdict(converted),
        scope_review_required=True,
        included_categories=m["included_categories"],
        installation_policy="No extra generic installation uplift",
        applicability_status="provisional",
        input_provenance=input_provenance or {},
    )
    installation = (
        InstallationBreakdown(amount, None, None, None, "not_provided", evidence)
        if m["cost_scope"] == "purchased_equipment"
        else None
    )
    return CostingResult(
        "provisional", estimate, amount, issues, evidence, installation=installation
    )
