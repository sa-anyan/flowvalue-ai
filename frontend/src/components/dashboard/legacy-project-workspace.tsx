"use client";
import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  type AssessmentRequest,
  type LegacyCell,
  type LegacyReference,
} from "@/lib/assessment";
import type { WorkspaceView } from "@/lib/workspace-navigation";

const names = [
  "Ideal case",
  "Turn-down for plant life",
  "Wind-power alternative",
  "Electricity price increase",
  "Mixed operation / maximum raw-material prices",
];
const gbp = (v: unknown) =>
  typeof v === "number"
    ? new Intl.NumberFormat("en-GB", {
        style: "currency",
        currency: "GBP",
        maximumFractionDigits: 0,
      }).format(v)
    : v == null
      ? "Not provided"
      : String(v);
const display = (v: unknown) =>
  typeof v === "number"
    ? v.toLocaleString("en-GB", { maximumFractionDigits: 6 })
    : v == null
      ? "—"
      : String(v);
function cell(
  ref: LegacyReference,
  sheet: string,
  address: string,
): LegacyCell | undefined {
  return ref.sheets.find((s) => s.name === sheet)?.cells[address];
}
function original(ref: LegacyReference, sheet: string, address: string) {
  const c = cell(ref, sheet, address);
  return c?.modified ? c.original_value : c?.value;
}
function source(ref: LegacyReference, scenario: number, key: string) {
  const map: Record<string, string[]> = {
    fixed: ["B4", "B19", "G4", "G19", "K4"],
    working: ["B5", "B20", "G5", "G20", "K5"],
    capital: ["B6", "B21", "G6", "G21", "K6"],
    fixedOpex: ["B7", "B22", "G7", "G22", "K7"],
    variableOpex: ["B8", "B23", "G8", "G23", "K8"],
    revenue: ["B9", "B24", "G9", "G24", "K9"],
    npv: ["B12", "B27", "G12", "G27", "K15"],
    payback: ["B11", "B26", "G11", "G26", "K14"],
  };
  const address = map[key][scenario];
  return { value: original(ref, "Summary", address), address };
}
function sourceRange(
  ref: LegacyReference,
  sheet: string,
  scenario: number,
  max: number,
): [number, number] {
  const rows = Object.entries(
    ref.sheets.find((s) => s.name === sheet)?.cells ?? {},
  )
    .filter(
      ([a, c]) =>
        /^A\d+$/.test(a) &&
        typeof c.value === "string" &&
        /^Scenario\s*[1-5]/i.test(c.value),
    )
    .map(([a, c]) => ({
      row: Number(a.slice(1)),
      number: Number(String(c.value).match(/Scenario\s*([1-5])/i)?.[1]),
    }))
    .sort((a, b) => a.row - b.row);
  const start = rows.find((r) => r.number === scenario + 1)?.row ?? 1;
  const end = rows.find((r) => r.row > start && r.number !== scenario + 1)?.row;
  return [start, end ? end - 1 : max];
}
export function LegacyProjectWorkspace({
  project,
  onProject,
  mode,
  capexTab = "summary",
}: {
  project: AssessmentRequest;
  onProject?: (p: AssessmentRequest) => void;
  mode: WorkspaceView | "process";
  capexTab?: string;
}) {
  const ref = project.legacy_reference!;
  const [scenario, setScenario] = useState(0),
    [editing, setEditing] = useState(false),
    [browserSheet, setBrowserSheet] = useState(ref.sheets[0].name);
  const changed = ref.sheets.reduce(
    (n, s) => n + Object.values(s.cells).filter((c) => c.modified).length,
    0,
  );
  const capitalColumn = scenario === 2 ? "E" : "B";
  const title =
    mode === "capex"
      ? `CAPEX · ${capexTab.replaceAll("-", " ")}`
      : mode === "main"
        ? "Project economics"
        : mode === "process"
          ? "Process equipment reference"
          : mode === "analysis"
            ? "Design basis & source workbook"
            : mode === "entry"
              ? "Legacy project inputs"
              : mode === "scenario"
                ? "Scenario comparison"
                : mode === "sensitivity"
                  ? "Legacy sensitivity cases"
                  : mode.toUpperCase();
  function edit(sheet: string, address: string, text: string) {
    if (!onProject) return;
    const previous = cell(ref, sheet, address);
    if (!previous) return;
    const value =
      typeof previous.value === "number" &&
      text.trim() !== "" &&
      Number.isFinite(Number(text))
        ? Number(text)
        : text;
    onProject({
      ...project,
      legacy_reference: {
        ...ref,
        sheets: ref.sheets.map((s) =>
          s.name !== sheet
            ? s
            : {
                ...s,
                cells: {
                  ...s.cells,
                  [address]: {
                    ...previous,
                    original_value: previous.modified
                      ? previous.original_value
                      : previous.value,
                    value,
                    modified: true,
                  },
                },
              },
        ),
      },
    });
  }
  function reset() {
    if (onProject)
      onProject({
        ...project,
        legacy_reference: {
          ...ref,
          sheets: ref.sheets.map((s) => ({
            ...s,
            cells: Object.fromEntries(
              Object.entries(s.cells).map(([a, c]) => [
                a,
                c.modified
                  ? { value: c.original_value ?? null, cached: c.cached }
                  : c,
              ]),
            ),
          })),
        },
      });
  }
  function download() {
    const a = document.createElement("a"),
      url = URL.createObjectURL(
        new Blob([JSON.stringify({ ...project, streams: [] }, null, 2)], {
          type: "application/json",
        }),
      );
    a.href = url;
    a.download = "flowvalue-legacy-reference-project.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function table(
    sheet: string,
    columns: string[],
    start: number,
    end: number,
    headers?: string[],
  ) {
    const data = ref.sheets.find((s) => s.name === sheet);
    if (!data) return <p>Source sheet not present: {sheet}</p>;
    const rows = Array.from(
      { length: end - start + 1 },
      (_, i) => i + start,
    ).filter((r) => columns.some((c) => data.cells[c + r]));
    return (
      <section
        className="panel legacy-source-table"
        key={sheet + start + columns.join("")}
      >
        <div className="panel-heading">
          <div>
            <h2>{sheet}</h2>
            <p>
              Source range {columns[0]}
              {start}:{columns.at(-1)}
              {end}. Original cached values; formulas are not executed.
            </p>
          </div>
        </div>
        <div className="table-scroll">
          <table className="capex-breakdown-table">
            <thead>
              <tr>
                <th>Row</th>
                {columns.map((c, i) => (
                  <th key={c}>{headers?.[i] ?? c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r}>
                  <td>{r}</td>
                  {columns.map((c) => {
                    const address = c + r,
                      v = data.cells[address];
                    return (
                      <td
                        key={address}
                        className={v?.modified ? "legacy-edited" : ""}
                      >
                        <span title={`${sheet}!${address}`}>
                          {editing && onProject && v ? (
                            <input
                              aria-label={`${sheet} ${address}`}
                              value={String(v.value ?? "")}
                              onChange={(e) =>
                                edit(sheet, address, e.target.value)
                              }
                            />
                          ) : (
                            display(v?.value)
                          )}
                        </span>
                        {v && (
                          <small className="legacy-cell-source">
                            {address}
                            {v.modified
                              ? " · edited placeholder"
                              : v.cached
                                ? " · cached formula result"
                                : ""}
                          </small>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    );
  }
  const allCards = [
    ["Fixed capital", "fixed"],
    ["Working capital", "working"],
    ["Total capital", "capital"],
    ["Fixed OPEX / year", "fixedOpex"],
    ["Variable OPEX / year", "variableOpex"],
    ["Revenue / year", "revenue"],
    ["NPV · source result", "npv"],
    ["Payback · source result", "payback"],
  ];
  const cards =
    mode === "capex"
      ? allCards.filter(([, key]) =>
          ["fixed", "working", "capital"].includes(key),
        )
      : mode === "opex"
        ? allCards.filter(([, key]) =>
            ["fixedOpex", "variableOpex"].includes(key),
          )
        : mode === "revenue"
          ? allCards.filter(([, key]) => key === "revenue")
          : allCards;
  const compare = names.map((name, i) => ({
    name: `Case ${i + 1}`,
    capital: source(ref, i, "capital").value,
    revenue: source(ref, i, "revenue").value,
    opex:
      Number(source(ref, i, "fixedOpex").value) +
      Number(source(ref, i, "variableOpex").value),
  }));
  const colYear = ["A", "L", "X", "AI", "AT"][scenario],
    colFlow = ["D", "O", "AA", "AL", "AW"][scenario],
    colCum = ["F", "Q", "AC", "AN", "AY"][scenario];
  const cash = Array.from({ length: 20 }, (_, i) => i + 32)
    .map((r) => ({
      year: original(ref, "NPV Calculation", colYear + r),
      cash: original(ref, "NPV Calculation", colFlow + r),
      cumulative:
        typeof original(ref, "NPV Calculation", colCum + r) === "number"
          ? Number(original(ref, "NPV Calculation", colCum + r)) * 1e6
          : null,
    }))
    .filter((v) => typeof v.year === "number");
  const discrepancy =
    source(ref, scenario, "capital").value !==
    original(ref, "Capex", capitalColumn + "27");
  const rawSheet = ref.sheets.find((s) => s.name === browserSheet)!;
  const rowsMax = Math.max(
    1,
    ...Object.keys(rawSheet.cells).map((a) => Number(a.match(/\d+$/)?.[0])),
  );
  const cols = [
    ...new Set(Object.keys(rawSheet.cells).map((a) => a.replace(/\d+$/, ""))),
  ].sort((a, b) => a.length - b.length || a.localeCompare(b));
  return (
    <div className="legacy-workspace">
      <section className="page-heading">
        <div>
          <div className="eyebrow">LEGACY REFERENCE PROJECT</div>
          <h1>{title}</h1>
          <p>{ref.source_name}</p>
        </div>
        <button className="capex-action-button" onClick={download}>
          Download reference project
        </button>
      </section>
      <section className="panel legacy-reference-toolbar">
        <label>
          Workbook scenario
          <select
            aria-label="Legacy workbook scenario"
            value={scenario}
            onChange={(e) => setScenario(Number(e.target.value))}
          >
            {names.map((name, i) => (
              <option key={name} value={i}>
                Scenario {i + 1} · {name}
              </option>
            ))}
          </select>
        </label>
        <div>
          <strong>GBP · original workbook figures</strong>
          <p>
            Reference snapshot. Source formulas and assumptions have not been
            industrially validated. No live engine calculations or AI research
            run in this view.
          </p>
        </div>
        {onProject && (
          <button
            className="capex-action-button"
            onClick={() => setEditing(!editing)}
          >
            {editing ? "Finish placeholder editing" : "Edit placeholders"}
          </button>
        )}
      </section>
      {changed > 0 && (
        <div className="engineering-warning" role="status">
          {changed} edited placeholders. Dependent totals and charts remain the
          original source snapshot and have not been recomputed.{" "}
          <button onClick={reset}>Restore source values</button>
        </div>
      )}
      {(mode === "opex" ||
        mode === "revenue" ||
        mode === "main" ||
        mode === "capex" ||
        mode === "scenario" ||
        mode === "analysis") && (
        <div className="legacy-metric-grid">
          {cards.map(([label, key]) => {
            const s = source(ref, scenario, key);
            return (
              <article className="panel" key={key}>
                <span>{label}</span>
                <strong>
                  {key === "payback" ? display(s.value) : gbp(s.value)}
                </strong>
                <small>
                  Summary!{s.address}
                  {changed ? " · original snapshot" : ""}
                </small>
              </article>
            );
          })}
        </div>
      )}
      {discrepancy &&
        (mode === "capex" || mode === "main" || mode === "scenario") && (
          <div className="engineering-warning">
            Workbook totals differ: Summary!
            {source(ref, scenario, "capital").address} ={" "}
            {gbp(source(ref, scenario, "capital").value)}; Capex!{capitalColumn}
            27 = {gbp(original(ref, "Capex", capitalColumn + "27"))}. Both
            source records are retained.
          </div>
        )}
      {(mode === "main" || mode === "scenario") && (
        <div className="legacy-chart-grid">
          <section className="panel">
            <h2>Workbook cash flow · scenario {scenario + 1}</h2>
            <p>
              NPV Calculation rows 32–51; GBP. Cached cumulative figures are
              converted from £millions for display.
            </p>
            <div className="chart-area">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={cash}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="year" />
                  <YAxis tickFormatter={(v) => `£${(v / 1e6).toFixed(0)}m`} />
                  <Tooltip formatter={(v) => gbp(v)} />
                  <Line
                    dataKey="cumulative"
                    name="Cumulative cash flow"
                    stroke="#277c69"
                    dot={false}
                  />
                  <Line
                    dataKey="cash"
                    name="Annual cash flow"
                    stroke="#b18b48"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>
          <section className="panel">
            <h2>Original scenario comparison</h2>
            <div className="chart-area">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={compare}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis tickFormatter={(v) => `£${(v / 1e6).toFixed(0)}m`} />
                  <Tooltip formatter={(v) => gbp(v)} />
                  <Bar dataKey="capital" fill="#277c69" name="Total capital" />
                  <Bar dataKey="revenue" fill="#b18b48" name="Annual revenue" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>
        </div>
      )}
      {mode === "capex" &&
        [
          "summary",
          "direct-costs",
          "indirect-costs",
          "working-capital",
          "validation",
        ].includes(capexTab) &&
        table(
          "Capex",
          scenario === 2 ? ["D", "E"] : ["A", "B"],
          capexTab === "direct-costs"
            ? 3
            : capexTab === "indirect-costs"
              ? 15
              : capexTab === "working-capital"
                ? 25
                : 1,
          capexTab === "direct-costs"
            ? 12
            : capexTab === "indirect-costs"
              ? 23
              : 27,
          ["Capital element", "Amount (GBP)"],
        )}
      {((mode === "capex" && capexTab === "equipment") ||
        mode === "process") && (
        <>
          {table("Task 2 equipments", ["A", "B", "C", "D", "E"], 2, 38, [
            "Equipment tag",
            "Description",
            "Original cost (USD)",
            "Original cost (GBP)",
            "Present installed cost (GBP)",
          ])}
          <p className="capex-caption">
            Equipment tags reproduce the workbook. Combined AB tags are
            retained. Mass/energy balances, design ratings and physical
            connections were not supplied; no connections or 3D geometry are
            invented.
          </p>
          {scenario === 2 &&
            table("Task 2 equipments", ["A", "B", "C", "D", "E"], 43, 48)}
        </>
      )}
      {mode === "capex" && capexTab === "assumptions" && (
        <>
          {table("Task 2 equipments", ["A", "B", "C", "D", "E"], 1, 2)}
          {table(
            "Equipments",
            ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"],
            1,
            17,
          )}
        </>
      )}
      {mode === "opex" &&
        table(
          "Opex",
          ["A", "B", "C", "D"],
          ...sourceRange(ref, "Opex", scenario, 354),
        )}
      {mode === "revenue" && (
        <>
          {table(
            "Revenue",
            ["A", "B", "C", "D"],
            ...sourceRange(ref, "Revenue", scenario, 259),
          )}
          {table("Revenue", ["B", "C", "D", "E", "F"], 1, 11)}
        </>
      )}
      {mode === "sensitivity" && (
        <>
          {table("ROI", ["A", "B", "C", "D", "E", "F", "G"], 3, 49)}
          {table("Task 2 equipments", ["A", "B", "C", "D", "E"], 49, 54)}
        </>
      )}
      {(mode === "entry" || mode === "analysis") && (
        <>
          {table(
            "Equipments",
            ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"],
            1,
            17,
          )}
          <section className="panel legacy-source-table">
            <h2>Source inventory</h2>
            <p>
              {ref.sheets.length} sheets imported. Workbook fingerprint:{" "}
              {ref.source_sha256.slice(0, 16)}…
            </p>
            <p>
              IRR, engineering conditions and market-risk probabilities are not
              inferred from this reference snapshot.
            </p>
          </section>
        </>
      )}
      <details className="panel legacy-source-browser">
        <summary>Inspect all original workbook data</summary>
        <label>
          Source worksheet
          <select
            aria-label="Legacy source worksheet"
            value={browserSheet}
            onChange={(e) => setBrowserSheet(e.target.value)}
          >
            {ref.sheets.map((s) => (
              <option key={s.name}>{s.name}</option>
            ))}
          </select>
        </label>
        {table(browserSheet, cols, 1, rowsMax)}
      </details>
    </div>
  );
}
