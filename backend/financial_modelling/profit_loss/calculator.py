"""P&L arithmetic distinct from cash spending and financing principal."""


def profit_loss(
    revenue, fixed, variable, startup, closure, depreciation, interest, gain, tax
):
    ebitda = revenue - fixed - variable - startup - closure
    ebit = ebitda - depreciation
    before_tax = ebit + gain - interest
    return ebitda, ebit, before_tax, before_tax - tax
