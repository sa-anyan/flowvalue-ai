"""End-to-end orchestration around existing canonical engines; no AI arithmetic."""

import copy
import dataclasses
from decimal import Decimal, InvalidOperation

from backend.capex import calculate_capex
from backend.capex.connectors import prepare_capex_inputs
from backend.capex.models import CapexInputs, WorkingCapital
from backend.equipment_costing.total_cost.calculator import calculate_total_cost
from backend.equipment_costing.unit_conversion import ConversionContext
from backend.financial_modelling import calculate_financials
from backend.financial_modelling.connectors.calculator import prepare_financial_inputs
from backend.financial_modelling.models import (
    DepreciationPolicy,
    FinancialAssumptions,
    Money,
    Spend,
)
from backend.opex import calculate_opex
from backend.opex.indexes.garrett.model import PLANT_BASE
from backend.opex.models import MoneyBase, OpexInputs
from backend.revenue import calculate_revenue
from backend.revenue.models import RevenueProject

from .codec import construct, plain
from .sizing import derive_size

SECTIONS = ("equipment", "capex", "revenue", "opex", "financial")


def empty_plan():
    return {key: [] if key == "equipment" else {} for key in SECTIONS}


def source_streams(report):
    result = []
    for entity in report["entities"]:
        if entity["kind"] != "material":
            continue
        flows = [
            v
            for v in entity["values"]
            if v.get("status") != "unresolved"
            and v["property"] == "mass_flow"
            and v.get("normalized_unit") == "kg/h"
            and v.get("normalized_value") is not None
        ]
        if len({str(v["normalized_value"]) for v in flows}) != 1:
            continue
        v = flows[0]
        result.append(
            {
                "id": entity["key"],
                "name": entity["identifier"] or entity["key"],
                "flow": {
                    "value": str(v["normalized_value"]),
                    "unit": "kg/h",
                    "rationale": "Source-supported parsed mass flow; not independent balance verification",
                    "source": f"{v['workbook']}!{v['sheet']}!{v['cell']}",
                    "uncertainty": "Workbook and formula-cache accuracy require engineering review",
                    "status": "source_supported",
                    "as_of": report.get("extracted_on", ""),
                },
                "source_references": [v["id"]],
                "boundary": "unresolved",
                "specifications": "",
            }
        )
    return result


def contracts():
    """Canonical model schemas supplied to the AI and advanced editor, not a second engine."""
    from pydantic import TypeAdapter

    return {
        name: TypeAdapter(cls).json_schema()
        for name, cls in {
            "capex": CapexInputs,
            "revenue": RevenueProject,
            "opex": OpexInputs,
            "financial_assumptions": FinancialAssumptions,
            "spend": Spend,
            "depreciation": DepreciationPolicy,
            "money": Money,
        }.items()
    }


def run(report, description, plan, *, progress=lambda *x: None):
    """Independent stage failures stay visible. Unpriced equipment never becomes zero."""
    outputs, objects = {}, {}
    exclusions = []

    def stage(name, calculate):
        progress(name, "running")
        try:
            result = calculate()
            objects[name] = result
            value = plain(result)
            outputs[name] = {
                "status": value.get("status", "calculated")
                if isinstance(value, dict)
                else "calculated",
                "result": value,
            }
        except (
            ValueError,
            TypeError,
            KeyError,
            ArithmeticError,
            AttributeError,
        ) as exc:
            outputs[name] = {
                "status": "unresolved",
                "issues": [str(exc)[:1500]],
                "result": None,
            }
        progress(name, outputs[name]["status"])

    def equipment():
        parsed = {e["key"]: e for e in report["entities"] if e["kind"] == "equipment"}
        chosen = {}
        for row in plan.get("equipment", []):
            key = row.get("equipment_key")
            if key not in parsed:
                reference = str(
                    key or row.get("equipment_tag") or row.get("identifier") or ""
                )
                token = "".join(c for c in reference.casefold() if c.isalnum())
                matches = [
                    k
                    for k, e in parsed.items()
                    if token
                    and token
                    == "".join(c for c in e["identifier"].casefold() if c.isalnum())
                ]
                if len(matches) == 1:
                    key = matches[0]
            if key in parsed and key not in chosen:
                chosen[key] = row
        rows = []
        for key, entity in parsed.items():
            proposal = chosen.get(key, {})
            options = copy.deepcopy(proposal.get("costing_options", {}))
            if isinstance(options.get("unit_context"), dict):
                options["unit_context"] = construct(
                    ConversionContext, options["unit_context"]
                )
            sizing_evidence = None
            sizing_issue = None
            try:
                size, size_unit, sizing_evidence = derive_size(proposal, report)
            except ValueError as exc:
                size, size_unit = None, proposal.get("size_unit")
                sizing_issue = str(exc)
            if isinstance(size, str):
                try:
                    size = float(Decimal(size))
                except (InvalidOperation, ValueError, OverflowError):
                    pass  # Canonical unit validator retains the unsupported value as an issue.
            rows.append(
                {
                    "equipment_tag": entity["identifier"] or key,
                    "curve_id": "external:reviewed-comparable" if proposal.get("external_quote") else proposal.get("curve_id"),
                    "external_quote": proposal.get("external_quote"),
                    "separate_scope_conflicts": True,
                    "size": size,
                    "size_unit": size_unit,
                    "quantity": proposal.get("quantity", 1),
                    "costing_options": options,
                    "parsed_source": {
                        "equipment_key": key,
                        "name": next(
                            (
                                v.get("normalized_value")
                                for v in reversed(entity["values"])
                                if v["property"] == "name"
                            ),
                            entity["identifier"],
                        ),
                        "classification": next(
                            (
                                v.get("normalized_value")
                                for v in reversed(entity["values"])
                                if v["property"] == "type"
                            ),
                            "",
                        ),
                        "stream_keys": entity.get("stream_keys", []),
                        "evidence": entity["values"],
                        "sizing": sizing_evidence,
                        "sizing_issue": sizing_issue,
                        "rationale": proposal.get(
                            "rationale", "No supported model/sizing supplied"
                        ),
                    },
                }
            )
        return calculate_total_cost(rows)

    stage("equipment", equipment)
    total = objects.get("equipment")
    priced = []
    if total:
        for line in total.equipment:
            if line.equipment_cost is not None and line.amount is not None:
                priced.append(line)
            else:
                exclusions.append(
                    {
                        "equipment_tag": line.equipment_tag,
                        "reason": "; ".join(line.issues)
                        or "Purchased component unavailable",
                        "status": "unpriced/excluded",
                        "cost": None,
                    }
                )

    def capex():
        if not priced:
            raise ValueError(
                "No priced purchased-equipment components; CAPEX is unresolved, not zero"
            )
        config = copy.deepcopy(plan.get("capex", {}))
        model = config.pop("model_id", "garrett")
        if model == "nottingham_lang":
            raise ValueError("Lang is a screening comparison only; select a detailed CAPEX methodology")
        delivery = config.pop("delivery_basis")
        config.pop("equipment", None)
        subset = dataclasses.replace(total, equipment=tuple(priced))
        prepared = prepare_capex_inputs(
            subset,
            process_type=config.pop("process_type"),
            delivery_basis=delivery,
            process_description=description,
        )
        config.pop("process_description", None)
        prepared = construct(CapexInputs, dict(plain(prepared), **config))
        try:
            screening = calculate_capex("nottingham_lang", dataclasses.replace(
                prepared, factor_selection="minimum", selected_factors={}, overrides={}, exclusions={},
                working_capital=WorkingCapital(excluded=True, rationale="Fixed-capital screening comparison only; working capital is not included")))
            objects["screening_comparisons"] = [{"method": "nottingham_lang", "result": plain(screening),
                "included_in_capex": False, "purpose": "Independent whole-plant screening comparison only; never added to detailed CAPEX"}]
        except (ValueError, TypeError):
            objects["screening_comparisons"] = [{"method": "nottingham_lang", "included_in_capex": False,
                                                 "status": "unavailable_for_selected_basis"}]
        return calculate_capex(model, prepared)

    stage("capex", capex)

    if plan.get("operating_economics"):
        from .operating_economics import calculate_operating_study

        def coupled():
            bundle = calculate_operating_study(
                report, description, plan["operating_economics"], objects.get("capex")
            )
            objects["joint_study"] = bundle
            return {
                "status": "calculated_preliminary",
                "methodology": "garrett",
                "annual_hours": str(bundle["detail"]["annual_hours"]),
                "basis": "One coupled consumption, sales, operating cost and financial scenario",
            }

        stage("operating_economics", coupled)
        bundle = objects.get("joint_study")
        if bundle:
            objects["financial_inputs"] = bundle["financial_inputs"]
            stage("revenue", lambda: bundle["revenue"])
            first = next(iter(bundle["opex"].values()))
            stage(
                "opex",
                lambda: {
                    "status": "calculated_preliminary",
                    "currency": first.basis.currency,
                    "price_period": first.basis.price_period,
                    "first_year_cash_opex": first.annual_cash_opex,
                    "first_year_fixed_opex": first.cash_fixed,
                    "first_year_variable_opex": first.cash_variable,
                    "years": {str(k): plain(v) for k, v in bundle["opex"].items()},
                    "first_year_lines": plain(first.lines),
                    "operating_detail": plain(bundle["detail"]),
                },
            )
            stage("financial", lambda: bundle["financial"])
        else:
            for missing in ("revenue", "opex", "financial"):
                outputs[missing] = {
                    "status": "unresolved",
                    "issues": outputs["operating_economics"].get("issues", []),
                    "result": None,
                }
        return {
            "stages": outputs,
            "screening_comparisons": objects.get("screening_comparisons", []),
            "exclusions": exclusions,
            "scope": "partial equipment scope"
            if exclusions
            else "parsed equipment scope; completeness not established",
            "financial_inputs": plain(objects.get("financial_inputs")),
            "notice": "Conditional engineering study; operating plan, quantities, prices and policies are editable. Capital exclusions carry into the complete financial schedule.",
        }

    def revenue():
        config = copy.deepcopy(plan.get("revenue", {}))
        # Physical quantities cannot be authored by an LLM or copied from an unrelated stream.
        source = {s["id"]: s for s in source_streams(report)}
        supplied = config.pop("streams", [])
        streams = []
        for row in supplied:
            if row["id"] not in source:
                raise ValueError(
                    "Revenue stream must reference a source-supported parsed mass flow"
                )
            original = copy.deepcopy(source[row["id"]])
            if row.get("flow") and row["flow"] != original["flow"]:
                raise ValueError("Revenue cannot replace a parsed physical flow")
            original["boundary"] = row.get("boundary", "unresolved")
            original["specifications"] = row.get("specifications", "")
            streams.append(original)
        config.update(streams=streams, process_description=description)
        project = construct(RevenueProject, config)
        return calculate_revenue(project, engineering_scenario=True)

    stage("revenue", revenue)

    def opex():
        config = copy.deepcopy(plan.get("opex", {}))
        if not config:
            raise ValueError(
                "Operating quantities, prices, staffing and reviewed category assumptions are missing"
            )
        base_input = construct(OpexInputs, config)
        cap = objects.get("capex")
        sales = objects.get("revenue")
        # Rebuild dependent bases on EVERY run; user prices/factors remain unchanged.
        results = {}
        years = [r.year for r in sales.annual] if sales and sales.annual else [1]
        for year in years:
            bases = {b.id: b for b in base_input.bases}
            if cap and cap.total_capex is not None:
                if (base_input.basis.currency, base_input.basis.price_period) != (
                    cap.currency,
                    cap.period,
                ):
                    raise ValueError(
                        "OPEX price currency/period must match capital base; supply dated alignment first"
                    )
                for key, amount in {
                    "fixed_capital": cap.fixed_capital,
                    "purchased_equipment": cap.purchased_equipment,
                    PLANT_BASE: cap.fixed_capital + cap.startup_expenses,
                }.items():
                    bases[key] = MoneyBase(
                        key,
                        amount,
                        base_input.basis,
                        "Current canonical CAPEX snapshot",
                    )
            if sales:
                if sales.basis != base_input.basis:
                    raise ValueError("Revenue and OPEX must share explicit price basis")
                annual = next(r for r in sales.annual if r.year == year)
                if annual.sales_revenue is not None:
                    bases["annual_revenue"] = MoneyBase(
                        "annual_revenue",
                        annual.sales_revenue,
                        base_input.basis,
                        "Current Revenue snapshot",
                    )
            # Reserved computed bases must never fall back to stale user-provided numbers.
            required = {
                a.base for a in base_input.assumptions if a.method == "percentage"
            }
            if required.intersection(
                {"fixed_capital", "purchased_equipment", PLANT_BASE}
            ) and (not cap or cap.total_capex is None):
                raise ValueError(
                    "Capital-dependent OPEX awaits a calculated CAPEX subset"
                )
            if "annual_revenue" in required and (
                not sales or any(r.sales_revenue is None for r in sales.annual)
            ):
                raise ValueError("Sales-dependent OPEX awaits calculated Revenue")
            results[year] = calculate_opex(
                inputs=dataclasses.replace(base_input, bases=tuple(bases.values()))
            )
        objects["opex_years"] = results
        return {
            "status": "calculated"
            if all(r.annual_cash_opex is not None for r in results.values())
            else "needs_review",
            "years": {str(k): plain(v) for k, v in results.items()},
        }

    stage("opex", opex)

    def financial():
        config = copy.deepcopy(plan.get("financial", {}))
        assumptions = construct(FinancialAssumptions, config.pop("assumptions"))
        if not (
            0 <= assumptions.construction_years <= 20
            and 1 <= assumptions.operating_years <= 100
        ):
            raise ValueError(
                "Local assessment supports at most 20 construction and 100 operating years"
            )
        spend = tuple(construct(Spend, r) for r in config.pop("capital_spend"))
        policies = {
            k: construct(DepreciationPolicy, v)
            for k, v in config.pop("depreciation_policies").items()
        }
        proceeds = {
            k: construct(Money, v) for k, v in config.pop("disposal_proceeds").items()
        }
        year_map = {int(k): v for k, v in config.pop("year_map").items()}
        cap = objects.get("capex")
        # A CEPCI period cannot silently be relabelled as a different price year.
        if str(config.get("price_year")) not in str(cap.period if cap else ""):
            raise ValueError(
                "Financial price year must agree with canonical equipment/CAPEX cost period"
            )
        inputs = prepare_financial_inputs(
            assumptions=assumptions,
            capex_result=objects["capex"],
            opex_by_revenue_year=objects["opex_years"],
            revenue_result=objects["revenue"],
            capital_spend=spend,
            depreciation_policies=policies,
            disposal_proceeds=proceeds,
            year_map=year_map,
            **config,
        )
        objects["financial_inputs"] = inputs
        return calculate_financials(inputs)

    stage("financial", financial)
    scope = (
        "partial equipment scope"
        if exclusions
        else "parsed equipment scope; completeness not established"
    )
    return {
        "stages": outputs,
        "screening_comparisons": objects.get("screening_comparisons", []),
        "exclusions": exclusions,
        "scope": scope,
        "financial_inputs": plain(objects.get("financial_inputs")),
        "notice": "Preliminary scenario. Source extraction is not industrial validation. All downstream totals apply only to the disclosed scope.",
    }
