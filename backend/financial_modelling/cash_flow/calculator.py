"""One set of accounting identities and discount conventions for all metrics."""

from decimal import Decimal


def point_factor(rate, year, convention):
    if convention == "discrete_end":
        if rate <= -1:
            raise ValueError("Discrete discount rate must exceed -100%")
        return (1 + rate) ** (-year)
    if convention in {"continuous_end", "garrett_uniform"}:
        return (-rate * year).exp()
    raise ValueError("Unsupported discount convention")


def recurring_factor(rate, year, convention):
    if year == 0 or convention != "garrett_uniform":
        return point_factor(rate, year, convention)
    if rate == 0:
        return Decimal(1)
    return ((-rate * (year - 1)).exp() - (-rate * year).exp()) / rate


def discount(recurring, point, rate, year, convention):
    return recurring * recurring_factor(rate, year, convention) + point * point_factor(
        rate, year, convention
    )


def cash_flows(
    net_income,
    depreciation,
    gain,
    working_change,
    capex,
    proceeds,
    draw,
    principal,
    project_recurring,
    project_point,
):
    operating = net_income + depreciation - gain - working_change
    investing = -capex + proceeds
    equity = operating + investing + draw - principal
    project = project_recurring + project_point
    return operating, investing, project, equity
