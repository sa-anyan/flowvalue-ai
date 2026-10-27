"use client";

import {
  Activity,
  ArrowUpRight,
  Check,
  Layers3,
  LoaderCircle,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";
import type { Assessment, AssessmentRequest } from "@/lib/assessment";
import { percent, usd } from "@/lib/assessment";
import { CapexChart, CashFlowChart, RiskChart } from "./charts";

type ChartView = "cumulative" | "waterfall";

export function MainDashboard({
  data,
  input,
  updating,
  error,
  discount,
  chartView,
  onChartViewChange,
}: {
  data: Assessment | null;
  input: AssessmentRequest | null;
  updating: boolean;
  error: string;
  discount: number;
  chartView: ChartView;
  onChartViewChange: (view: ChartView) => void;
}) {
  const risk = data?.uncertainty;
  const annualOpex = input
    ? input.financial.fixed_opex_usd_per_year +
      input.financial.variable_opex_usd_per_year
    : null;

  return (
    <div className="main-dashboard-summary">
      <section
        className={`metric-grid main-dashboard-metrics ${updating && data ? "is-updating" : ""}`}
        aria-label="Main dashboard financial metrics"
        aria-busy={updating}
      >
        <div className="metric-card">
          <div className="metric-label">
            CAPEX <Layers3 size={17} />
          </div>
          <strong data-testid="capex">
            {data ? usd(data.bom.total_bare_module_cost_usd, true) : "—"}
          </strong>
          <div className="metric-footer">
            <span>Equipment investment</span>
            <small>Bare-module cost · USD</small>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">
            Annual OPEX <Activity size={17} />
          </div>
          <strong data-testid="opex">
            {annualOpex === null ? "—" : usd(annualOpex, true)}
          </strong>
          <div className="metric-footer">
            <span>Fixed + variable operating cost</span>
            <small>Current scenario · USD/year</small>
          </div>
        </div>
        <div className="metric-card metric-featured">
          <div className="metric-label">
            Net present value <ArrowUpRight size={17} />
          </div>
          <strong data-testid="npv">
            {data ? usd(data.financial.npv_usd, true) : "—"}
          </strong>
          <div className="metric-footer">
            <span>
              {data
                ? data.financial.npv_usd >= 0
                  ? "Positive project value"
                  : "Below investment hurdle"
                : "Calculating project value"}
            </span>
            <small>at {discount}% discount</small>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">
            Internal rate of return <Activity size={17} />
          </div>
          <strong data-testid="irr" className={data?.financial.irr === null ? "metric-text" : undefined}>
            {data
              ? data.financial.irr === null
                ? "Not defined"
                : percent(data.financial.irr)
              : "—"}
          </strong>
          <div className="metric-footer">
            <span>Annual project return</span>
            <small>IRR / DCFROR</small>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">
            Levelized cost of product <Layers3 size={17} />
          </div>
          <strong data-testid="lcop">
            {data ? `$${data.financial.lcop_usd_per_unit.toFixed(2)}` : "—"}
            <em> / unit</em>
          </strong>
          <div className="metric-footer">
            <span>Lifetime production cost</span>
            <small>Pre-tax LCOP</small>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">
            Discounted payback <RotateCcw size={17} />
          </div>
          <strong data-testid="payback" className={data?.financial.discounted_payback_years === null ? "metric-text" : undefined}>
            {data
              ? data.financial.discounted_payback_years === null
                ? "Not recovered"
                : <>{data.financial.discounted_payback_years.toFixed(1)} <em>years</em></>
              : "—"}
          </strong>
          <div className="metric-footer">
            <span>Time to recover CAPEX</span>
            <small>Discounted basis</small>
          </div>
        </div>
      </section>
      <section className="panel cash-panel">
        <div className="panel-heading">
          <div>
            <h2>{chartView === "waterfall" ? "Annual cash-flow waterfall" : "Cumulative cash flow"}</h2>
            <p>The long view on your process economics.</p>
          </div>
          <div className="chart-view-control">
            <select
              aria-label="Cash flow chart view"
              value={chartView}
              onChange={(e) => onChartViewChange(e.target.value as ChartView)}
            >
              <option value="cumulative">Cumulative curve</option>
              <option value="waterfall">Cash-flow waterfall</option>
            </select>
            <span className="quiet-badge">{input?.financial.operating_years ?? "—"}-year horizon</span>
          </div>
        </div>
        <div className="line-legend">
          <span><i />{chartView === "waterfall" ? "Operating cash flow" : "Undiscounted"}</span>
          <span><i className="gold" />{chartView === "waterfall" ? "Initial investment" : "Discounted"}</span>
          <span className="calculation-status" role="status">
            {error ? "Check inputs" : updating ? <><LoaderCircle size={12} className="spin" /> Recalculating</> : <><Check size={12} /> Up to date</>}
          </span>
        </div>
        <div className="chart-area">
          {data ? <CashFlowChart data={data} view={chartView} /> : <div className="chart-placeholder"><LoaderCircle className="spin" />Connecting to the financial engine</div>}
        </div>
        <div className="chart-bottom">
          <span>Initial investment</span>
          <strong>{data ? usd(data.bom.total_bare_module_cost_usd) : "—"}</strong>
          <span className="chart-bottom-note">Bare-module CAPEX at year zero</span>
        </div>
      </section>
      <div className="secondary-grid">
        <section className="panel" id="risk">
          <div className="panel-heading">
            <div>
              <h2>Every outcome, considered.</h2>
              <p>NPV distribution from {risk?.iterations.toLocaleString() ?? "1,000"} Monte Carlo scenarios.</p>
            </div>
            <span className="quiet-badge">±20% cost risk</span>
          </div>
          <div className="risk-chart">
            {data ? <RiskChart data={data} /> : <div className="chart-placeholder">Waiting for the risk engine</div>}
          </div>
          <div className="percentile-grid">
            {([
              ["P10 · lower", risk?.p10_npv_usd],
              ["P50 · median", risk?.p50_npv_usd],
              ["P90 · upper", risk?.p90_npv_usd],
            ] as const).map(([label, value]) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{typeof value === "number" ? usd(value, true) : "—"}</strong>
              </div>
            ))}
          </div>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Where your capital goes</h2>
              <p>Bare module cost by equipment category.</p>
            </div>
            <Layers3 size={18} className="muted-icon" />
          </div>
          {data ? <CapexChart data={data} /> : <div className="chart-placeholder">Waiting for the costing engine</div>}
          <div className="probability-note">
            <ShieldCheck size={17} />
            <span>Positive NPV in <strong>{risk ? percent(risk.probability_positive_npv) : "—"}</strong> of simulated scenarios.</span>
          </div>
        </section>
      </div>
    </div>
  );
}
