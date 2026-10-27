"""Two-page executive summary with bounded grouped BOM and actual risk histogram."""

from collections import defaultdict
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.engine.costing import EquipmentBOM
from app.financial.dcf_model import FinancialResult, MonteCarloResult

INK = colors.HexColor("#182E2B")
TEAL = colors.HexColor("#167566")
PALE = colors.HexColor("#EFF5F2")


def money(value: float) -> str:
    return f"(${abs(value):,.0f})" if value < 0 else f"${value:,.0f}"


def build_pdf(
    bom: EquipmentBOM,
    financial: FinancialResult,
    risk: MonteCarloResult,
    *,
    demo: bool = False,
) -> bytes:
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=(612, 792),
        leftMargin=42,
        rightMargin=42,
        topMargin=46,
        bottomMargin=42,
        title="FlowValue AI - Executive Summary",
        author="FlowValue AI",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="FVTitle",
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=30,
            textColor=INK,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FVSection",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=17,
            textColor=INK,
            spaceBefore=12,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FVBody",
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=INK,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FVSmall",
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#5B6D67"),
            alignment=TA_LEFT,
        )
    )

    def p(text, style="FVBody"):
        return Paragraph(escape(text), styles[style])

    def table(rows, widths=None, padding=10):
        t = Table(rows, colWidths=widths, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), INK),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), padding),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PALE, colors.white]),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("LINEBELOW", (0, -1), (-1, -1), 0.5, TEAL),
                ]
            )
        )
        return t

    f = financial.inputs
    irr = "Not defined" if financial.irr is None else f"{financial.irr:.1%}"
    payback = (
        "Not recovered"
        if financial.discounted_payback_years is None
        else f"{financial.discounted_payback_years:.1f} years"
    )
    story = [
        p("FLOWVALUE AI  /  PROCESS ECONOMICS", "FVSmall"),
        Spacer(1, 12),
        p("Executive summary", "FVTitle"),
        p(
            "Synthetic demonstration scenario"
            if demo
            else "Current assessment scenario",
            "FVSmall",
        ),
        Spacer(1, 16),
        table(
            [
                ["NPV", "IRR / DCFROR", "LCOP, pre-tax"],
                [
                    money(financial.npv_usd),
                    irr,
                    f"${financial.lcop_usd_per_unit:,.2f}/unit",
                ],
            ],
            [176, 176, 176],
        ),
        Spacer(1, 10),
        p(
            f"{f.operating_years}-year operating life at a {f.discount_rate:.1%} discount rate. "
            f"Discounted payback: {payback}. Annual production: {f.plant_capacity_units_per_year * f.capacity_factor:,.0f} units."
        ),
        p("Capital allocation", "FVSection"),
    ]
    groups = defaultdict(lambda: [0, 0.0])
    for item in bom.items:
        groups[item.kind][0] += item.quantity
        groups[item.kind][1] += item.quantity * item.bare_module_cost_usd
    group_rows = [["Equipment category", "Units", "Bare module cost"]]
    for kind, (quantity, cost) in sorted(
        groups.items(), key=lambda pair: pair[1][1], reverse=True
    ):
        group_rows.append([kind.replace("_", " ").title(), str(quantity), money(cost)])
    group_rows.append(
        [
            "Total CAPEX (BOM basis)",
            str(sum(x.quantity for x in bom.items)),
            money(bom.total_bare_module_cost_usd),
        ]
    )
    scope_warnings = list(dict.fromkeys(
        n for n in financial.warnings
        if n.startswith(("INCOMPLETE EQUIPMENT SCOPE:", "MIXED EQUIPMENT SCOPE:"))
    ))
    for warning in scope_warnings[:2]:
        story.append(p(warning[:280], "FVSmall"))
    story += [
        table(group_rows, [280, 65, 183], padding=5),
        p(
            f"Annual OPEX: {money(f.fixed_opex_usd_per_year + f.variable_opex_usd_per_year)}. "
            f"Annual revenue: {money(f.plant_capacity_units_per_year * f.capacity_factor * f.product_selling_price_usd_per_unit)}."
        ),
        p("Cumulative cash flow", "FVSection"),
    ]
    chart = Drawing(528, 135)
    values = [row.cumulative_free_cash_flow_usd for row in financial.cash_flows]
    low, high = min(0, min(values)), max(0, max(values))
    span = high - low or 1
    points = [
        (35 + i / max(1, len(values) - 1) * 470, 20 + (v - low) / span * 90)
        for i, v in enumerate(values)
    ]
    zero = 20 + (0 - low) / span * 90
    chart.add(Line(35, zero, 505, zero, strokeColor=colors.HexColor("#CCDAD4")))
    chart.add(PolyLine(points, strokeColor=TEAL, strokeWidth=2.5))
    chart.add(String(35, 3, "Year 0", fontSize=8, fillColor=INK))
    chart.add(String(455, 3, f"Year {f.operating_years}", fontSize=8, fillColor=INK))
    chart.add(
        String(
            35, 120, f"Range: {money(low)} to {money(high)}", fontSize=8, fillColor=INK
        )
    )
    story += [
        chart,
        p(
            "Constant-dollar, unlevered cash flow. Full CAPEX at year zero. No debt, working capital or salvage. Credits follow the explicit scenario assumptions.",
            "FVSmall",
        ),
        PageBreak(),
        p("Risk & calculation basis", "FVTitle"),
        p(
            f"{risk.iterations:,} simulated scenarios | seed {risk.seed} | independent uniform cost variation +/-{risk.variation_fraction:.0%}",
            "FVSmall",
        ),
        Spacer(1, 14),
        table(
            [
                ["P10 NPV", "P50 NPV", "P90 NPV"],
                [
                    money(risk.p10_npv_usd),
                    money(risk.p50_npv_usd),
                    money(risk.p90_npv_usd),
                ],
            ],
            [176, 176, 176],
        ),
        Spacer(1, 10),
        p(
            f"Probability of positive NPV: {risk.probability_positive_npv:.1%}. "
            "P10 is the lower NPV percentile; P90 is the upper percentile."
        ),
        p("NPV distribution", "FVSection"),
    ]
    histogram = Drawing(528, 130)
    max_count = max((b.count for b in risk.histogram), default=1) or 1
    width = 480 / max(len(risk.histogram), 1)
    for i, bin_ in enumerate(risk.histogram):
        histogram.add(
            Rect(
                24 + i * width,
                22,
                max(1, width - 2),
                bin_.count / max_count * 85,
                fillColor=TEAL,
                strokeColor=None,
            )
        )
    histogram.add(String(24, 6, money(risk.min_npv_usd), fontSize=8, fillColor=INK))
    histogram.add(String(400, 6, money(risk.max_npv_usd), fontSize=8, fillColor=INK))
    story += [
        histogram,
        p("Cost exposure", "FVSection"),
        p(
            f"Feedstock: {money(f.feedstock_opex_usd_per_year)}/year. Utilities: {money(f.utility_opex_usd_per_year)}/year. "
            "These are included in total variable OPEX, not added twice. Price draws are held constant over each scenario's life."
        ),
        p("Estimate basis", "FVSection"),
        p(
            f"CEPCI target/reference: {bom.settings.cepci_current:g}/{bom.settings.cepci_base:g}. Capital stress multiplier: {bom.settings.capital_cost_multiplier:g}x. "
            f"Source basis (user supplied): {bom.settings.cepci_basis[:160]}. Full source record in workbook. Turton ranges apply unless extrapolation enabled."
        ),
        p(
            "Straight-line depreciation; taxes floored at zero with no loss carryforward. LCOP is before tax and credits. "
            + (
                f"Incentive scenario: {f.incentive.name[:100]}, ${f.incentive.rate_usd_per_unit:g}/unit, {f.incentive.duration_years} years from Y{f.incentive.start_year}, {f.incentive.treatment}. Eligibility: user-confirmed scenario; see workbook evidence."
                if f.incentive.enabled
                else "Production incentives disabled."
            )
        ),
        p("Engineering review notes", "FVSection"),
    ]
    warnings = list(
        dict.fromkeys(
            financial.warnings
            + risk.warnings
            + [warning for item in bom.items for warning in item.warnings]
        )
    )
    for warning in warnings[:4]:
        story.append(p(warning[:240], "FVSmall"))
    if len(warnings) > 4:
        story.append(
            p(
                f"{len(warnings) - 4} additional notes are included in the Excel model.",
                "FVSmall",
            )
        )
    story.append(
        p(
            "Bare module CAPEX excludes offsites, contingency and owner costs. Mechanical dimensions are screening estimates. Full equipment detail and editable financial formulas are in the companion Excel model.",
            "FVSmall",
        )
    )

    def footer(canvas, document):
        canvas.setStrokeColor(TEAL)
        canvas.line(42, 34, 570, 34)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(INK)
        canvas.drawString(
            42, 21, "FlowValue AI  /  Preliminary techno-economic assessment"
        )
        canvas.drawRightString(570, 21, f"{document.page} / 2")

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
