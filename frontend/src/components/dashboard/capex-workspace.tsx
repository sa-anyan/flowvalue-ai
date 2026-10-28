"use client";

import Link from "next/link";
import {
  capitalGroup as capexGroup,
  capitalAmount as capexAmount,
  capitalScope,
  capitalScopes,
  capitalGroupLabels,
  capitalRowIssues,
  type CapitalGroup as Group,
} from "@/lib/capex-analysis";
import { CapexGuide } from "./capex-guide";
import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  CircleHelp,
  Plus,
} from "lucide-react";
import {
  kindLabels,
  usd,
  type Assessment,
  type AssessmentRequest,
  type Stream,
} from "@/lib/assessment";
import { newCostItem, newStudy, type CostItem, type Study } from "@/lib/study";

export type CapexTab =
  | "summary"
  | "equipment"
  | "direct-costs"
  | "indirect-costs"
  | "working-capital"
  | "assumptions"
  | "validation";

export const capexPages: { tab: CapexTab; label: string; href: string }[] = [
  { tab: "summary", label: "Summary", href: "/capex/summary" },
  { tab: "equipment", label: "Equipment", href: "/capex/equipment" },
  { tab: "direct-costs", label: "Direct Costs", href: "/capex/direct-costs" },
  {
    tab: "indirect-costs",
    label: "Indirect Costs",
    href: "/capex/indirect-costs",
  },
  {
    tab: "working-capital",
    label: "Working Capital",
    href: "/capex/working-capital",
  },
  {
    tab: "assumptions",
    label: "Assumptions & Sources",
    href: "/capex/assumptions",
  },
  {
    tab: "validation",
    label: "Validation / Checks",
    href: "/capex/validation",
  },
];

export function capexTabFromPath(pathname: string): CapexTab {
  const value = pathname.split("/")[2];
  return capexPages.find((page) => page.tab === value)?.tab ?? "summary";
}

export { capexGroup, capexAmount };
function groupItems(project: AssessmentRequest | null, group: Group) {
  return (project?.study?.cost_items ?? []).filter(
    (item) => item.cost_type === "capex" && capexGroup(item) === group,
  );
}
const palette = [
  "#277C69",
  "#88AFA0",
  "#D9AB67",
  "#7A95B3",
  "#A48CA6",
  "#C48C78",
];
const money = (value: number | null) =>
  value === null ? "Not established" : usd(value);
const total = (rows: CostItem[]) =>
  rows.reduce((sum, row) => sum + (capexAmount(row) ?? 0), 0);
const hasMissing = (rows: CostItem[]) =>
  rows.some(
    (row) =>
      ["missing", "unsupported"].includes(row.status) ||
      (row.status === "included" && capexAmount(row) === null),
  );

export function CapexSummary({
  project,
  data,
  streams,
  updating,
  error,
  onProject,
}: {
  project: AssessmentRequest | null;
  data: Assessment | null;
  streams: Stream[];
  updating: boolean;
  error: string;
  onProject: (p: AssessmentRequest) => void;
}) {
  const equipmentCost = data?.bom.total_purchased_equipment_cost_usd ?? null;
  const installedCost = data?.bom.total_bare_module_cost_usd ?? null;
  const studyItems = (project?.study?.cost_items ?? []).filter(
    (item) => item.cost_type === "capex",
  );
  const direct = groupItems(project, "direct-costs");
  const indirect = groupItems(project, "indirect-costs");
  const working = groupItems(project, "working-capital");
  const unclassified = groupItems(project, "unclassified");
  const planningTotal = total(studyItems);
  const equipmentBreakdown = useMemo(() => {
    const buckets = new Map<string, number>();
    for (const item of data?.bom.items ?? []) {
      const name = kindLabels[item.kind] ?? item.kind;
      buckets.set(
        name,
        (buckets.get(name) ?? 0) + item.bare_module_cost_usd * item.quantity,
      );
    }
    return [...buckets]
      .map(([name, value]) => ({ name, value }))
      .filter((v) => v.value > 0);
  }, [data]);
  const largestEquipment = useMemo(
    () =>
      [...(data?.bom.items ?? [])]
        .map((item) => ({
          name: item.unit_id,
          value: item.bare_module_cost_usd * item.quantity,
        }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 8),
    [data],
  );
  const registerBreakdown = [
    { name: "Direct", value: total(direct), href: "/capex/direct-costs" },
    { name: "Indirect", value: total(indirect), href: "/capex/indirect-costs" },
    {
      name: "Working capital",
      value: total(working),
      href: "/capex/working-capital",
    },
    {
      name: "Unclassified",
      value: total(unclassified),
      href: "/capex/validation",
    },
  ].filter((v) => v.value > 0);
  const warningCount =
    (data?.bom.items.reduce((n, item) => n + item.warnings.length, 0) ?? 0) +
    studyItems.filter(
      (item) =>
        item.status === "missing" ||
        (item.status === "included" && capexAmount(item) === null),
    ).length +
    unclassified.length;
  return (
    <div className="capex-hub" aria-label="CAPEX summary dashboard">
      <div className="capex-intro">
        <div>
          <span className="capex-kicker">CAPITAL ESTIMATE · LIVE PROJECT</span>
          <h2>Capital at a glance</h2>
          <p>
            Cost composition, project evidence and capital scope from the active
            model. No historical spreadsheet costs are substituted for missing
            project data.
          </p>
        </div>
        <Link className="capex-text-link" href="/capex/validation">
          <CircleHelp size={15} /> {warningCount} scope and cost checks{" "}
          <ArrowUpRight size={14} />
        </Link>
      </div>
      <div className="capex-kpis">
        <article className="capex-kpi capex-kpi-primary">
          <span>Model CAPEX · bare module</span>
          <strong>{money(installedCost)}</strong>
          <small>
            Financial engine input · excludes offsites and full project capital
          </small>
        </article>
        <article className="capex-kpi">
          <span>Purchased equipment</span>
          <strong>{money(equipmentCost)}</strong>
          <small>Calculated equipment purchases · USD</small>
        </article>
        <article className="capex-kpi">
          <span>Additional planning ledger</span>
          <strong>
            {studyItems.some((item) => capexAmount(item) !== null)
              ? usd(planningTotal)
              : studyItems.length
                ? "Not quantified"
                : "Not provided"}
          </strong>
          <small>Planning-only · not added to model CAPEX</small>
        </article>
        <article className="capex-kpi">
          <span>Total project investment</span>
          <strong className="capex-pending">Not established</strong>
          <small>
            Requires a reviewed, non-overlapping total-capital estimate
          </small>
        </article>
      </div>
      {error ? (
        <p className="capex-notice" role="alert">
          Calculation unavailable: {error}
        </p>
      ) : updating ? (
        <p className="capex-notice" role="status">
          Recalculating current scenario. Displayed estimates may be stale.
        </p>
      ) : null}
      {project && <CapexGuide project={project} onProject={onProject} />}
      <div className="capex-chart-grid">
        <section className="panel capex-chart-panel">
          <div className="panel-heading">
            <div>
              <h3>Equipment capital allocation</h3>
              <p>Bare-module CAPEX by equipment type</p>
            </div>
          </div>
          {equipmentBreakdown.length ? (
            <div className="capex-donut">
              <ResponsiveContainer width="100%" height={240} minWidth={0}>
                <PieChart>
                  <Pie
                    data={equipmentBreakdown}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={66}
                    outerRadius={99}
                    paddingAngle={2}
                  >
                    {equipmentBreakdown.map((item, index) => (
                      <Cell
                        key={item.name}
                        fill={palette[index % palette.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => usd(Number(value))} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="capex-empty">
              Import or size equipment to display a capital allocation chart.
            </div>
          )}
        </section>
        <section className="panel capex-chart-panel">
          <div className="panel-heading">
            <div>
              <h3>Largest equipment investments</h3>
              <p>Quantity-weighted bare-module estimates, USD</p>
            </div>
          </div>
          {largestEquipment.length ? (
            <div className="capex-bar">
              <ResponsiveContainer width="100%" height={260} minWidth={0}>
                <BarChart
                  data={largestEquipment}
                  layout="vertical"
                  margin={{ left: 0, right: 22, top: 6, bottom: 0 }}
                >
                  <CartesianGrid
                    stroke="var(--border)"
                    strokeDasharray="3 4"
                    horizontal={false}
                  />
                  <XAxis
                    type="number"
                    tickFormatter={(v) => usd(v, true)}
                    tick={{ fontSize: 10 }}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={72}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip formatter={(v) => usd(Number(v))} />
                  <Bar
                    dataKey="value"
                    name="Bare module"
                    fill="#277C69"
                    radius={[0, 5, 5, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="capex-empty">
              Equipment-level chart appears when costing results are ready.
            </div>
          )}
        </section>
      </div>
      <section className="panel capex-breakdown">
        <div className="panel-heading">
          <div>
            <h3>Capital cost build-up</h3>
            <p>
              The legacy estimate structure, populated only where the current
              project provides valid values
            </p>
          </div>
          <Link href="/capex/direct-costs" className="capex-text-link">
            Edit cost register <ArrowUpRight size={14} />
          </Link>
        </div>
        <div className="table-scroll">
          <table className="capex-breakdown-table">
            <thead>
              <tr>
                <th>Capital element</th>
                <th>Basis</th>
                <th>Current amount (USD)</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              <tr className="capex-group-row">
                <th colSpan={4}>Direct costs</th>
              </tr>
              <tr>
                <td>Purchased equipment</td>
                <td>Costed equipment register</td>
                <td>{money(equipmentCost)}</td>
                <td>Engine output</td>
              </tr>
              <tr>
                <td>Installed / bare-module equipment</td>
                <td>
                  Existing module calculation; not additive to purchased
                  equipment
                </td>
                <td>{money(installedCost)}</td>
                <td>Engine output</td>
              </tr>
              {direct.map((item) => (
                <CapexSummaryRow key={item.item_id} item={item} />
              ))}
              <CapexPendingRows
                items={direct}
                names={[
                  "Installation",
                  "Instrumentation and control",
                  "Piping",
                  "Electrical",
                  "Yard improvements",
                  "Buildings",
                  "Service facilities",
                  "Land",
                ]}
              />
              <tr className="capex-group-row">
                <th colSpan={4}>Indirect costs</th>
              </tr>
              {indirect.map((item) => (
                <CapexSummaryRow key={item.item_id} item={item} />
              ))}
              <CapexPendingRows
                items={indirect}
                names={[
                  "Engineering and supervision",
                  "Construction expenses",
                  "Legal fees and taxes",
                  "Contractor fee",
                  "Contingency",
                ]}
              />
              <tr className="capex-group-row">
                <th colSpan={4}>Working capital</th>
              </tr>
              {working.map((item) => (
                <CapexSummaryRow key={item.item_id} item={item} />
              ))}
              {!working.length && (
                <tr>
                  <td>Working capital allowance</td>
                  <td>
                    Inventory, payables, receivables and start-up cash, as
                    applicable
                  </td>
                  <td>—</td>
                  <td>Not established</td>
                </tr>
              )}
              {unclassified.length > 0 && (
                <>
                  <tr className="capex-group-row">
                    <th colSpan={4}>Awaiting cost classification</th>
                  </tr>
                  {unclassified.map((item) => (
                    <CapexSummaryRow key={item.item_id} item={item} />
                  ))}
                </>
              )}
            </tbody>
          </table>
        </div>
        <p className="capex-caption">
          <AlertTriangle size={15} /> These categories are not summed into a
          full-project CAPEX: the current financial engine uses bare-module
          equipment CAPEX, while the separate study ledger is planning-only.
          Combining them without checking overlapping installation allowances
          would double-count costs.
        </p>
      </section>
      {registerBreakdown.length > 0 && (
        <section className="panel capex-planning-panel">
          <div className="panel-heading">
            <div>
              <h3>Planning ledger composition</h3>
              <p>
                Independently recorded capital items; separate from engine CAPEX
              </p>
            </div>
          </div>
          <div className="capex-register-bars">
            {registerBreakdown.map((row) => (
              <Link
                key={row.name}
                href={row.href}
                className="capex-register-row"
              >
                <span>{row.name}</span>
                <strong>{usd(row.value)}</strong>
                <span className="capex-register-track">
                  <i
                    style={{
                      width:
                        String(Math.max(1, (row.value / planningTotal) * 100)) +
                        "%",
                    }}
                  />
                </span>
              </Link>
            ))}
          </div>
          {(hasMissing(studyItems) || unclassified.length > 0) && (
            <p className="capex-caption">
              The register includes incomplete or unclassified entries; the
              composition chart reflects quantified included amounts only.
            </p>
          )}
        </section>
      )}
      <section className="panel capex-project-panel">
        <div className="panel-heading">
          <div>
            <h3>Project-specific capital context</h3>
            <p>
              Additional indicators appear only when supplied by project files
              or design/stream records
            </p>
          </div>
        </div>
        <div className="capex-context-grid">
          <div>
            <span>Equipment units</span>
            <strong>{project?.costing.equipment.length ?? "—"}</strong>
            <small>Current BOM</small>
          </div>
          <div>
            <span>Imported process streams</span>
            <strong>{streams.length}</strong>
            <small>Mass/energy balance evidence</small>
          </div>
          <div>
            <span>Cost evidence records</span>
            <strong>{project?.study?.evidence.length ?? 0}</strong>
            <small>Design inputs, quotations and sources</small>
          </div>
          <div>
            <span>Project location</span>
            <strong>
              {project?.study?.design_basis.location || "Not specified"}
            </strong>
            <small>Review regional capital allowances</small>
          </div>
        </div>
        {project?.study?.design_basis.source_context && (
          <p className="capex-context-note">
            <strong>Design sources:</strong>{" "}
            {project.study.design_basis.source_context}
          </p>
        )}
        {streams.length > 0 && (
          <>
            <h3 className="capex-stream-heading">
              Largest imported process streams
            </h3>
            <div className="table-scroll">
              <table className="capex-breakdown-table">
                <thead>
                  <tr>
                    <th>Stream ID</th>
                    <th>From</th>
                    <th>To</th>
                    <th>Mass flow (kg/h)</th>
                  </tr>
                </thead>
                <tbody>
                  {[...streams]
                    .sort((a, b) => b.mass_flow_kg_h - a.mass_flow_kg_h)
                    .slice(0, 5)
                    .map((stream) => (
                      <tr key={stream.stream_id}>
                        <td>{stream.stream_id}</td>
                        <td>{stream.source_unit || "Not mapped"}</td>
                        <td>{stream.destination_unit || "Not mapped"}</td>
                        <td>
                          {stream.mass_flow_kg_h.toLocaleString("en-GB", {
                            maximumFractionDigits: 1,
                          })}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        <p className="capex-caption">
          Stream quantities inform what equipment might be required; they do not
          independently establish a supplier price, installed cost or process
          design.
        </p>
      </section>
    </div>
  );
}

function CapexPendingRows({
  items,
  names,
}: {
  items: CostItem[];
  names: string[];
}) {
  return (
    <>
      {names
        .filter(
          (name) =>
            !items.some((item) =>
              item.description
                .trim()
                .toLowerCase()
                .includes(name.toLowerCase()),
            ),
        )
        .map((name) => (
          <tr key={name}>
            <td>{name}</td>
            <td className="capex-muted-cell">
              Requires project-specific costing basis
            </td>
            <td>—</td>
            <td>Not established</td>
          </tr>
        ))}
    </>
  );
}

function CapexSummaryRow({ item }: { item: CostItem }) {
  return (
    <tr>
      <td>{item.description}</td>
      <td>
        {item.basis ||
          (item.quantity !== null && item.rate_usd !== null
            ? String(item.quantity) + " × " + usd(item.rate_usd)
            : "Basis missing")}
      </td>
      <td>{money(capexAmount(item))}</td>
      <td>
        {item.status === "included"
          ? capexAmount(item) === null
            ? "Inputs incomplete"
            : "Planning only"
          : item.status.replaceAll("_", " ")}
      </td>
    </tr>
  );
}

export function CapexCostRegister({
  project,
  onProject,
  group,
}: {
  project: AssessmentRequest;
  onProject: (project: AssessmentRequest) => void;
  group: "direct-costs" | "indirect-costs" | "working-capital";
}) {
  const study = project.study ?? newStudy();
  const rows = study.cost_items.filter(
    (item) => item.cost_type === "capex" && capexGroup(item) === group,
  );
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [preset, setPreset] = useState("");
  const templates = capitalScopes.filter((s) => s.group === group);
  const visible = rows.filter(
    (item) =>
      (!query ||
        (item.description + " " + item.basis)
          .toLowerCase()
          .includes(query.toLowerCase())) &&
      (filter === "all" ||
        (filter === "needs-review"
          ? capitalRowIssues(item, project).length > 0
          : item.status === filter)),
  );
  const title = capitalGroupLabels[group];
  const edit = (items: CostItem[]) =>
    onProject({ ...project, study: { ...study, cost_items: items } });
  const change = (id: string, update: Partial<CostItem>) =>
    edit(
      study.cost_items.map((item) =>
        item.item_id === id ? { ...item, ...update } : item,
      ),
    );
  function add() {
    if (study.cost_items.length >= 500) return;
    const scope = templates.find((s) => s.code === preset);
    const item = {
      ...newCostItem("CAP-" + crypto.randomUUID(), "capex"),
      category: title + (scope ? " / " + scope.label : ""),
      description: scope?.label ?? "New capital cost",
    };
    edit([...study.cost_items, item]);
  }
  const unresolved = rows.filter(
    (item) => capitalRowIssues(item, project).length > 0,
  ).length;
  return (
    <section className="panel capex-register-page">
      <div className="panel-heading">
        <div>
          <span className="capex-kicker">CAPITAL WORK PACKAGES</span>
          <h2>{title}</h2>
          <p>
            Build the estimate from scoped quantities, current USD rates and
            linked evidence.
          </p>
        </div>
      </div>
      <div className="capital-register-metrics">
        <div>
          <span>Quantified included subtotal</span>
          <strong>
            {rows.some((r) => capexAmount(r) !== null)
              ? usd(total(rows))
              : "Not established"}
          </strong>
          <small>Separate from financial-model CAPEX</small>
        </div>
        <div>
          <span>Recorded items</span>
          <strong>{rows.length}</strong>
          <small>{unresolved} need costing or evidence review</small>
        </div>
        <div>
          <span>Scope boundary</span>
          <strong>
            {group === "working-capital"
              ? "Funding requirement"
              : "Planning estimate"}
          </strong>
          <small>
            {group === "working-capital"
              ? "Not a depreciable equipment purchase"
              : "Review installed-equipment overlap"}
          </small>
        </div>
      </div>
      {group === "working-capital" && (
        <div className="capital-guidance">
          <strong>Build the working-capital basis</strong>
          <p>
            Review inventory holding, receivable and payable terms, and
            operating cash. Document the net funding requirement and timing as
            an allowance. A universal fixed-capital percentage is not assumed.
          </p>
        </div>
      )}
      <div className="capital-register-toolbar">
        <label>
          Add a work package
          <select
            aria-label="Capital work package to add"
            value={preset}
            onChange={(e) => setPreset(e.target.value)}
          >
            <option value="">Custom cost item</option>
            {templates.map((s) => (
              <option key={s.code} value={s.code}>
                {s.code} · {s.label}
              </option>
            ))}
          </select>
        </label>
        <button
          className="capex-action-button"
          onClick={add}
          disabled={study.cost_items.length >= 500}
        >
          <Plus size={15} />
          Add cost item
        </button>
        <label>
          Find in this register
          <input
            aria-label="Search capital register"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Description or basis"
          />
        </label>
        <label>
          Show
          <select
            aria-label="Capital register status filter"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">All items</option>
            <option value="needs-review">Needs review</option>
            <option value="included">Included</option>
            <option value="excluded">Excluded</option>
            <option value="not_applicable">Not applicable</option>
          </select>
        </label>
      </div>
      <p className="capital-register-count">
        {visible.length} of {rows.length} items shown. Filters do not change
        subtotals.
      </p>
      {!rows.length && (
        <div className="capex-empty">
          Start with a named work package or a custom item. Quantities and
          prices remain blank until established for this project.
        </div>
      )}
      {rows.length > 0 && !visible.length && (
        <div className="capex-empty">No items match these filters.</div>
      )}
      {visible.map((item) => {
        const scope = capitalScope(item),
          issues = capitalRowIssues(item, project),
          amount = capexAmount(item);
        return (
          <details
            id={"capital-" + item.item_id}
            className="capital-cost-detail"
            key={item.item_id}
            open={rows.length === 1}
          >
            <summary>
              <span className="capital-cost-title">
                <small>
                  {scope?.code ?? "CUSTOM"} · {item.status.replaceAll("_", " ")}
                </small>
                <strong>{item.description}</strong>
              </span>
              <span className="capital-cost-amount">
                {amount === null ? "Unpriced / outside subtotal" : usd(amount)}
                <small>
                  {issues.length
                    ? `${issues.length} review points`
                    : "Documented input"}
                </small>
              </span>
            </summary>
            <div className="capex-edit-row">
              <div className="capital-guidance">
                <strong>Basis to establish</strong>
                <p>
                  {scope?.prompt ??
                    "Describe the scope, quantity basis, pricing method and boundary of this cost. Link applicable supporting evidence."}
                </p>
              </div>
              <div className="capex-edit-grid">
                <label>
                  Description
                  <input
                    aria-label={item.item_id + " description"}
                    maxLength={300}
                    value={item.description}
                    onChange={(e) =>
                      change(item.item_id, { description: e.target.value })
                    }
                  />
                </label>
                <label>
                  Work package
                  <select
                    aria-label={item.item_id + " work package"}
                    value={scope?.code ?? "custom"}
                    onChange={(e) => {
                      const next = capitalScopes.find(
                        (s) => s.code === e.target.value,
                      );
                      change(item.item_id, {
                        category: next
                          ? capitalGroupLabels[next.group] + " / " + next.label
                          : title,
                      });
                    }}
                  >
                    <option value="custom">Custom / unassigned package</option>
                    {capitalScopes.map((s) => (
                      <option key={s.code} value={s.code}>
                        {s.code} · {s.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Status
                  <select
                    aria-label={item.item_id + " status"}
                    value={item.status}
                    onChange={(e) =>
                      change(item.item_id, {
                        status: e.target.value as CostItem["status"],
                      })
                    }
                  >
                    {[
                      "included",
                      "excluded",
                      "missing",
                      "unsupported",
                      "not_applicable",
                    ].map((v) => (
                      <option key={v} value={v}>
                        {v.replaceAll("_", " ")}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Quantity
                  <input
                    aria-label={item.item_id + " quantity"}
                    type="number"
                    min="0"
                    step="any"
                    value={item.quantity ?? ""}
                    onChange={(e) =>
                      change(item.item_id, {
                        quantity:
                          e.target.value === "" ? null : Number(e.target.value),
                      })
                    }
                  />
                </label>
                <label>
                  Unit
                  <input
                    aria-label={item.item_id + " unit"}
                    maxLength={80}
                    value={item.unit}
                    onChange={(e) =>
                      change(item.item_id, { unit: e.target.value })
                    }
                  />
                </label>
                <label>
                  Rate (USD/unit)
                  <input
                    aria-label={item.item_id + " rate"}
                    type="number"
                    min="0"
                    step="any"
                    value={item.rate_usd ?? ""}
                    onChange={(e) =>
                      change(item.item_id, {
                        rate_usd:
                          e.target.value === "" ? null : Number(e.target.value),
                      })
                    }
                  />
                </label>
                <label>
                  Project allocation (0–1)
                  <input
                    aria-label={item.item_id + " allocation"}
                    type="number"
                    min="0"
                    max="1"
                    step=".05"
                    value={item.allocation_fraction}
                    onChange={(e) => {
                      if (e.target.value !== "")
                        change(item.item_id, {
                          allocation_fraction: Number(e.target.value),
                        });
                    }}
                  />
                </label>
                <label>
                  Cost ownership
                  <select
                    aria-label={item.item_id + " ownership"}
                    value={item.cost_arrangement}
                    onChange={(e) =>
                      change(item.item_id, {
                        cost_arrangement: e.target
                          .value as CostItem["cost_arrangement"],
                      })
                    }
                  >
                    <option value="incremental">New capital cost</option>
                    <option value="allocated_existing">
                      Allocated existing
                    </option>
                    <option value="charged_elsewhere">Charged elsewhere</option>
                  </select>
                </label>
                <label className="capex-wide-field">
                  Method, price date, currency conversion and scope boundary
                  <textarea
                    aria-label={item.item_id + " basis"}
                    maxLength={2000}
                    value={item.basis}
                    onChange={(e) =>
                      change(item.item_id, { basis: e.target.value })
                    }
                    placeholder="Quote/calculation reference; what is included; source cost year; USD conversion if applicable; exclusions"
                  />
                </label>
              </div>
              <fieldset className="capital-evidence">
                <legend>Linked cost evidence</legend>
                {study.evidence.length ? (
                  study.evidence.map((e) => (
                    <label key={e.evidence_id}>
                      <input
                        type="checkbox"
                        disabled={!item.evidence_ids.includes(e.evidence_id) && item.evidence_ids.length >= 20}
                        checked={item.evidence_ids.includes(e.evidence_id)}
                        onChange={(v) =>
                          change(item.item_id, {
                            evidence_ids: v.target.checked
                              ? [...item.evidence_ids, e.evidence_id]
                              : item.evidence_ids.filter(
                                  (id) => id !== e.evidence_id,
                                ),
                          })
                        }
                      />
                      <span>
                        {e.title}
                        <small>
                          {e.kind} · {e.observed_on ?? "Date missing"}
                        </small>
                      </span>
                    </label>
                  ))
                ) : (
                  <p>
                    No sources recorded.{" "}
                    <Link href="/dashboard">
                      Add evidence in the shared study workspace.
                    </Link>
                  </p>
                )}
              </fieldset>
              <div className="capital-calculation">
                <span>Quantity × USD rate × allocation</span>
                <strong>
                  {amount === null
                    ? "Not included in subtotal"
                    : `${item.quantity} × ${usd(item.rate_usd!)} × ${item.allocation_fraction} = ${usd(amount)}`}
                </strong>
              </div>
              {issues.length > 0 && (
                <ul className="capital-review-points">
                  {issues.map((issue) => (
                    <li key={issue}>{issue}</li>
                  ))}
                </ul>
              )}
              <div className="capital-row-actions">
                <button
                  className="capex-text-link"
                  onClick={() =>
                    change(item.item_id, { quantity: 1, unit: "lot" })
                  }
                >
                  Use one lump-sum lot
                </button>
                <button
                  className="capex-text-link"
                  aria-label={"Delete " + item.description}
                  onClick={() =>
                    edit(
                      study.cost_items.filter(
                        (x) => x.item_id !== item.item_id,
                      ),
                    )
                  }
                >
                  Remove item
                </button>
              </div>
            </div>
          </details>
        );
      })}
      <p className="capex-caption">
        <AlertTriangle size={14} /> Enter current USD rates. Excluded and
        unpriced entries remain visible, and no register allowance is
        automatically added to the DCF.
      </p>
    </section>
  );
}

export function CapexSources({
  project,
}: {
  project: AssessmentRequest | null;
}) {
  const evidence = project?.study?.evidence ?? [];
  const study = project?.study;
  return (
    <section className="panel capex-source-page">
      <h2>CAPEX assumptions & sources</h2>
      <p>
        Reference basis for equipment costing and project allowances. Add or
        edit detailed design evidence in the shared study workspace.
      </p>
      <div className="capex-context-grid">
        <div>
          <span>Model currency</span>
          <strong>USD</strong>
          <small>
            Record dated currency conversions in each cost basis. Historical
            quotations are not current rates.
          </small>
        </div>
        <div>
          <span>Current cost index</span>
          <strong>{project?.costing.settings.cepci_current ?? "—"}</strong>
          <small>
            {project?.costing.settings.cepci_basis ?? "Manual assumption"}
          </small>
        </div>
        <div>
          <span>Reference cost index</span>
          <strong>{project?.costing.settings.cepci_base ?? "—"}</strong>
          <small>Index basis used by equipment correlations</small>
        </div>
        <div>
          <span>Design/site basis</span>
          <strong>{study?.design_basis.site_type ?? "Unknown"}</strong>
          <small>
            {study?.design_basis.location || "Location not provided"}
          </small>
        </div>
      </div>
      <h3>Evidence register</h3>
      {evidence.length ? (
        <div className="table-scroll">
          <table className="capex-breakdown-table">
            <thead>
              <tr>
                <th>Evidence</th>
                <th>Type</th>
                <th>Observed</th>
                <th>Reference</th>
              </tr>
            </thead>
            <tbody>
              {evidence.map((e) => (
                <tr key={e.evidence_id}>
                  <td>{e.title}</td>
                  <td>{e.kind}</td>
                  <td>{e.observed_on || "Not dated"}</td>
                  <td>
                    {e.source_url ? (
                      <a href={e.source_url} rel="noreferrer" target="_blank">
                        {e.reference || "Open source"}
                      </a>
                    ) : (
                      e.reference || "Not provided"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="capex-empty">
          No evidence records have been added yet.
        </div>
      )}
      <Link className="capex-text-link" href="/dashboard">
        Open design basis & evidence <ArrowUpRight size={14} />
      </Link>
    </section>
  );
}

export function CapexValidation({
  project,
  data,
  streams,
  error,
  onProject,
}: {
  project: AssessmentRequest | null;
  data: Assessment | null;
  streams: Stream[];
  error: string;
  onProject: (project: AssessmentRequest) => void;
}) {
  const items = (project?.study?.cost_items ?? []).filter(
    (item) => item.cost_type === "capex",
  );
  const unclassified = items.filter(
    (item) => capexGroup(item) === "unclassified",
  );
  const equipmentWarnings =
    data?.bom.items.flatMap((x) =>
      x.warnings.map((message) => x.unit_id + ": " + message),
    ) ?? [];
  const problems = [
    ...(error ? ["Calculation failed: " + error] : []),
    ...equipmentWarnings,
    ...items
      .filter(
        (item) =>
          item.status === "missing" ||
          (item.status === "included" && capexAmount(item) === null),
      )
      .map((item) => item.description + ": estimate incomplete"),
    ...(project?.is_demo
      ? ["Project is using synthetic demonstration data."]
      : []),
    "Total project capital and working-capital schedule have not been reconciled to the financial engine.",
    ...(!streams.length
      ? [
          "No imported process streams: verify the equipment scope against the design and mass/energy balance.",
        ]
      : []),
  ];
  function classify(item: CostItem, category: string) {
    if (!project) return;
    const study: Study = project.study ?? newStudy();
    onProject({
      ...project,
      study: {
        ...study,
        cost_items: study.cost_items.map((x) =>
          x.item_id === item.item_id ? { ...x, category } : x,
        ),
      },
    });
  }
  return (
    <section className="panel capex-checks-page">
      <div className="panel-heading">
        <div>
          <h2>CAPEX validation & scope checks</h2>
          <p>
            Incomplete estimates and engineering evidence are visible before
            results are presented as a full capital investment.
          </p>
        </div>
      </div>
      <div className="capex-check-banner">
        <AlertTriangle size={19} />
        <span>
          Screening estimate only: bare-module equipment costs are connected to
          the DCF. Other CAPEX allowances must be reviewed and reconciled
          separately.
        </span>
      </div>
      {project && (
        <CapexGuide project={project} onProject={onProject} detailed />
      )}
      <div className="capex-check-list">
        {problems.map((issue, i) => (
          <div key={i}>
            <AlertTriangle size={15} />
            <span>{issue}</span>
          </div>
        ))}
        {data && !equipmentWarnings.length && (
          <div>
            <CheckCircle2 size={15} />
            <span>
              No equipment-specific costing warnings returned by the calculation
              engine.
            </span>
          </div>
        )}
      </div>
      {unclassified.length > 0 && (
        <>
          <h3>Classify capital register items</h3>
          <p>
            Unrecognised categories are not silently assigned to direct or
            indirect capital.
          </p>
          {unclassified.map((item) => (
            <div className="capex-classification" key={item.item_id}>
              <span>
                {item.description}{" "}
                <small>({item.category || "No category"})</small>
              </span>
              <select
                aria-label={"Classify " + item.description}
                value=""
                onChange={(e) => classify(item, e.target.value)}
              >
                <option value="">Select category</option>
                <option value="Direct Costs">Direct Costs</option>
                <option value="Indirect Costs">Indirect Costs</option>
                <option value="Working Capital">Working Capital</option>
              </select>
            </div>
          ))}
        </>
      )}
      <Link className="capex-text-link" href="/capex/summary">
        Return to CAPEX summary <ArrowUpRight size={14} />
      </Link>
    </section>
  );
}
