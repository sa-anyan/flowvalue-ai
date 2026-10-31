"""Translate saved commercial decisions to canonical immutable revenue inputs."""

from dataclasses import replace

from ..models import AvoidedCost, CommercialLine, PaymentYear
from .mass_energy_balance import annual_billable
from .process_description import verify_context


def commercial_inputs(report, description, config, basis, hours, ramp, assumption):
    lines, savings = [], []
    known_sources = {
        v.get("id")
        for entity in report.get("entities", [])
        for v in entity.get("values", [])
    }
    known_sources.update(
        entity.get("id_evidence", {}).get("id") for entity in report.get("entities", [])
    )
    for item in config.get("commercial_lines", []):
        verify_context(item, description)
        if item["arrangement"] == "llm_proposed" and any(
            ref not in known_sources for ref in item.get("source_references", [])
        ):
            raise ValueError(
                "LLM commercial sources must reference supplied engineering evidence; market research needs explicit consent"
            )
        years, refs = [], list(item.get("source_references", []))
        expected = list(ramp)
        if [y["year"] for y in item["years"]] != expected:
            raise ValueError(
                "Commercial annual schedule must match operating years in order"
            )
        for row in item["years"]:
            quantity = row["quantity"]
            quantity_source = (
                "Explicit contractual/commercial quantity assumption, not workbook data"
            )
            quantity_status = (
                "llm_estimate"
                if item["arrangement"] == "llm_proposed"
                else "user_assumption"
            )
            if item.get("stream_key"):
                result = annual_billable(report, item, hours, ramp[row["year"]])
                quantity = result["annual_quantity"]
                quantity_source = str(result)
                quantity_status = "source_supported"
                refs.append(quantity_source)
            elif item.get("property") != "contract_quantity":
                raise ValueError(
                    "Measured revenue quantities need an actual stream; use contract_quantity for an explicit commercial assumption"
                )
            unit = item["quantity_unit"]
            rate_unit = (
                basis.currency
                + "/"
                + unit
                + {"per_unit": "", "annual": "/year", "monthly": "/month"}[
                    item["rate_period"]
                ]
            )

            def a(value, units, item=item):
                return replace(
                    assumption(
                        value,
                        units,
                        config,
                        item["rationale"],
                        status="llm_estimate"
                        if item["arrangement"] == "llm_proposed"
                        else "user_assumption",
                        source="; ".join(item.get("source_references", []))
                        or "Saved commercial assumption",
                    ),
                    uncertainty=item["uncertainty"],
                )

            years.append(
                PaymentYear(
                    row["year"],
                    assumption(
                        quantity,
                        unit,
                        config,
                        item["rationale"],
                        source=quantity_source,
                        status=quantity_status,
                    ),
                    a(row["rate"], rate_unit),
                    a(row["fixed_payment"], basis.currency + "/year"),
                    a(row["minimum_quantity"], unit),
                    a(row["minimum_payment"], basis.currency + "/year"),
                    a(row["availability"], "fraction"),
                    a(row["escalation"], "fraction/year"),
                    row["periods"],
                )
            )
        lines.append(
            CommercialLine(
                item["id"],
                item["name"],
                item["category"],
                item["payment_id"],
                item["quantity_unit"],
                item["rate_period"],
                item["arrangement"],
                item["rationale"],
                tuple(dict.fromkeys(refs)),
                tuple(years),
                item.get("stream_key") or "",
                item.get("included", True),
                item["fixed_variable_distinct"],
                item["eligibility_basis"],
                item.get("exclusion_reason", ""),
            )
        )
    for item in config.get("avoided_costs", []):
        savings.append(
            AvoidedCost(
                item["id"],
                item["target_opex_id"],
                item["rationale"],
                tuple(
                    (
                        row["year"],
                        assumption(
                            row["amount"],
                            basis.currency + "/year",
                            config,
                            item["rationale"],
                        ),
                    )
                    for row in item["years"]
                ),
                item["already_applied"],
            )
        )
    return tuple(lines), tuple(savings)
