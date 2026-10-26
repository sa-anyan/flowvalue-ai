"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Assessment, kindLabels, usd } from "@/lib/assessment";

const palette = ["#277C69", "#A8CBB7", "#DDB477", "#879BB5", "#B79BC0"];
const tooltip = {
  background: "var(--card)",
  border: "1px solid var(--border)",
  borderRadius: 10,
  color: "var(--foreground)",
  fontSize: 12,
};
const axis = { fill: "var(--muted-foreground)", fontSize: 11 };

export function CashFlowChart({
  data,
  view = "cumulative",
}: {
  data: Assessment;
  view?: "cumulative" | "waterfall";
}) {
  if (view === "waterfall") {
    const rows = data.financial.cash_flows.map((r, i) => {
      const previous =
        i === 0
          ? 0
          : data.financial.cash_flows[i - 1].cumulative_free_cash_flow_usd;
      return {
        ...r,
        range: [
          Math.min(previous, r.cumulative_free_cash_flow_usd),
          Math.max(previous, r.cumulative_free_cash_flow_usd),
        ],
      };
    });
    return (
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <BarChart
          data={rows}
          margin={{ top: 12, right: 12, left: 0, bottom: 4 }}
        >
          <CartesianGrid
            stroke="var(--border)"
            strokeDasharray="3 5"
            vertical={false}
          />
          <XAxis
            dataKey="year"
            tick={axis}
            axisLine={false}
            tickLine={false}
            minTickGap={25}
            tickFormatter={(v) => `Y${v}`}
          />
          <YAxis
            tick={axis}
            axisLine={false}
            tickLine={false}
            width={63}
            tickFormatter={(v) => usd(v, true)}
          />
          <ReferenceLine y={0} stroke="var(--muted-foreground)" />
          <Tooltip
            content={({ active, payload, label }) =>
              active && payload?.length ? (
                <div style={tooltip} className="waterfall-tooltip">
                  Year {label}
                  <br />
                  Free cash flow:{" "}
                  {usd(
                    rows.find((r) => r.year === Number(label))
                      ?.free_cash_flow_usd ?? 0,
                  )}
                </div>
              ) : null
            }
          />
          <Bar dataKey="range" name="Cash flow" radius={[2, 2, 0, 0]}>
            {rows.map((r) => (
              <Cell
                key={r.year}
                fill={r.free_cash_flow_usd < 0 ? "#C58D69" : "#277C69"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }
  return (
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <AreaChart
        data={data.financial.cash_flows}
        margin={{ top: 12, right: 12, left: 0, bottom: 4 }}
      >
        <defs>
          <linearGradient id="cashFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#277C69" stopOpacity={0.19} />
            <stop offset="100%" stopColor="#277C69" stopOpacity={0.01} />
          </linearGradient>
        </defs>
        <CartesianGrid
          stroke="var(--border)"
          strokeDasharray="3 5"
          vertical={false}
        />
        <XAxis
          dataKey="year"
          tick={axis}
          axisLine={false}
          tickLine={false}
          minTickGap={25}
          tickFormatter={(v) => `Y${v}`}
        />
        <YAxis
          tick={axis}
          axisLine={false}
          tickLine={false}
          width={63}
          tickFormatter={(v) => usd(v, true)}
        />
        <Tooltip
          contentStyle={tooltip}
          labelFormatter={(v) => `Year ${v}`}
          formatter={(v, name) => [
            usd(Number(v)),
            name === "cumulative_free_cash_flow_usd"
              ? "Cumulative cash flow"
              : "Discounted cash flow",
          ]}
        />
        <ReferenceLine
          y={0}
          stroke="var(--muted-foreground)"
          strokeDasharray="3 3"
        />
        <Area
          type="monotone"
          dataKey="cumulative_free_cash_flow_usd"
          stroke="#277C69"
          strokeWidth={2.5}
          fill="url(#cashFill)"
        />
        <Area
          type="monotone"
          dataKey="cumulative_discounted_free_cash_flow_usd"
          stroke="#B4945C"
          strokeWidth={1.8}
          strokeDasharray="5 4"
          fill="transparent"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function RiskChart({ data }: { data: Assessment }) {
  const risk = data.uncertainty;
  if (!risk) return <p>No risk analysis available.</p>;
  const bins = risk.histogram.map((b) => ({
    npv: (b.lower_npv_usd + b.upper_npv_usd) / 2,
    count: b.count,
  }));
  const markers = [
    ["P10", risk.p10_npv_usd],
    ["P50", risk.p50_npv_usd],
    ["P90", risk.p90_npv_usd],
  ] as const;
  const getBin = (v: number) =>
    bins.reduce(
      (best, b) => (Math.abs(b.npv - v) < Math.abs(best.npv - v) ? b : best),
      bins[0],
    ).npv;
  return (
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <BarChart
        data={bins}
        margin={{ top: 24, right: 12, left: -20, bottom: 2 }}
      >
        <CartesianGrid
          stroke="var(--border)"
          vertical={false}
          strokeDasharray="3 5"
        />
        <XAxis
          dataKey="npv"
          tick={axis}
          tickLine={false}
          axisLine={false}
          minTickGap={45}
          tickFormatter={(v) => usd(v, true)}
        />
        <YAxis tick={axis} tickLine={false} axisLine={false} />
        <Tooltip
          contentStyle={tooltip}
          labelFormatter={(v) => `NPV ≈ ${usd(Number(v))}`}
          formatter={(v) => [Number(v), "Scenarios"]}
        />
        <Bar dataKey="count" fill="#83AF9C" radius={[3, 3, 0, 0]} />
        {markers.map(([label, value]) => (
          <ReferenceLine
            key={label}
            x={getBin(value)}
            stroke={label === "P50" ? "#277C69" : "#B4945C"}
            strokeDasharray="4 3"
            label={{
              value: label,
              position: "top",
              fill: "var(--muted-foreground)",
              fontSize: 10,
            }}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

export function CapexChart({ data }: { data: Assessment }) {
  const totals = data.bom.items.reduce<Record<string, number>>((acc, item) => {
    const label = kindLabels[item.kind];
    acc[label] = (acc[label] ?? 0) + item.bare_module_cost_usd * item.quantity;
    return acc;
  }, {});
  const values = Object.entries(totals)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
  return (
    <div className="capex-layout">
      <div className="donut-wrap">
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <PieChart>
            <Pie
              data={values}
              dataKey="value"
              innerRadius="65%"
              outerRadius="90%"
              paddingAngle={4}
              stroke="none"
            >
              {values.map((v, i) => (
                <Cell key={v.name} fill={palette[i % palette.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltip} formatter={(v) => usd(Number(v))} />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-center">
          <span>Total CAPEX</span>
          <strong>{usd(data.bom.total_bare_module_cost_usd, true)}</strong>
        </div>
      </div>
      <div className="chart-legend">
        {values.map((v, i) => (
          <div key={v.name}>
            <i style={{ background: palette[i % palette.length] }} />
            <span>{v.name}</span>
            <strong>
              {((v.value / data.bom.total_bare_module_cost_usd) * 100).toFixed(
                1,
              )}
              %
            </strong>
          </div>
        ))}
      </div>
    </div>
  );
}
