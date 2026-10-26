"use client";

import { apiFetch } from "@/lib/client-api";

import {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  FileSpreadsheet,
  FlaskConical,
  Layers3,
  LayoutDashboard,
  LoaderCircle,
  Moon,
  Plus,
  RotateCcw,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Sun,
  Trash2,
  Upload,
  Waves,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import {
  apiError,
  Assessment,
  AssessmentRequest,
  defaults,
  EquipmentSpec,
  fieldLabels,
  Kind,
  kindLabels,
  percent,
  Stream,
  usd,
} from "@/lib/assessment";
import { ProjectAccount } from "./project-account";
import { EngineeringTools } from "./engineering-tools";
import {
  importScopeNotes,
  workspaceKey,
  readWorkspace,
  writeWorkspace,
  type Workspace,
  type NativeImport,
} from "@/lib/workspace";
import { CapexChart, CashFlowChart, RiskChart } from "./charts";
import {
  UniversalAdvisor,
  defaultContext,
  type Suggestion,
} from "./universal-advisor";

function RangeControl({
  label,
  value,
  min,
  max,
  step = 1,
  unit,
  change,
  detail,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit: string;
  change: (v: number) => void;
  detail: string;
}) {
  return (
    <div className="range-control">
      <div className="range-label">
        <label>{label}</label>
        <output>
          {value > 0 && min < 0 ? "+" : ""}
          {value}
          {unit}
        </output>
      </div>
      <Slider
        label={label}
        value={[value]}
        min={min}
        max={max}
        step={step}
        onValueChange={(v) => change(Array.isArray(v) ? v[0] : v)}
      />
      <div className="range-bounds">
        <span>
          {min}
          {unit}
        </span>
        <span>
          {max}
          {unit}
        </span>
      </div>
      <p>{detail}</p>
    </div>
  );
}
function NumberField({
  label,
  value,
  change,
  min = 0,
  step = "any",
}: {
  label: string;
  value: number;
  change: (v: number) => void;
  min?: number;
  step?: string | number;
}) {
  return (
    <label className="number-field">
      <span>{label}</span>
      <input
        type="number"
        value={Number.isFinite(value) ? value : ""}
        min={min}
        step={step}
        onChange={(e) => change(Number(e.target.value))}
      />
    </label>
  );
}

export default function Dashboard() {
  const [base, setBase] = useState<AssessmentRequest | null>(null);
  const [controls, setControls] = useState({
    feed: 0,
    utility: 0,
    discount: 10,
    life: 20,
    capex: 0,
    price: 0,
    fixed: 0,
    other: 0,
  });
  const [envelope, setEnvelope] = useState<{
    signature: string;
    data: Assessment;
  } | null>(null);
  const [failure, setFailure] = useState<{
    signature: string;
    message: string;
  } | null>(null);
  const [initialError, setInitialError] = useState("");
  const [retry, setRetry] = useState(0);
  const [dark, setDark] = useState(false);
  const [chartView, setChartView] = useState<"cumulative" | "waterfall">(
    "cumulative",
  );
  const [expanded, setExpanded] = useState<string | null>(null);
  const [kind, setKind] = useState<Kind>("heat_exchanger");
  const [nativeImport, setNativeImport] = useState<NativeImport | null>(null);
  const [streams, setStreams] = useState<Stream[]>([]);
  const authChanged = useCallback((clear = false) => {
    if (clear) {
      setBase(null);
      setEnvelope(null);
      setStreams([]);
      setNativeImport(null);
    }
    setRetry((r) => r + 1);
  }, []);

  const [filename, setFilename] = useState("");
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [exporting, setExporting] = useState("");
  const [notice, setNotice] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);
  useEffect(() => {
    const controller = new AbortController();
    apiFetch("/api/demo", { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) throw new Error(await apiError(r));
        return r.json();
      })
      .then((data: AssessmentRequest) => {
        const local = readWorkspace();
        if (local) {
          data = local.native_import
            ? {
                ...local.project,
                engineering_notes: [
                  ...new Set([
                    ...(local.project.engineering_notes || []),
                    ...importScopeNotes(
                      local.native_import,
                      local.project.costing.equipment,
                    ),
                  ]),
                ].slice(0, 100),
              }
            : local.project;
          setStreams(local.streams || []);
          setNativeImport(local.native_import || null);
        }
        setBase(data);
        setControls({
          feed: 0,
          utility: 0,
          discount: data.financial.discount_rate * 100,
          life: data.financial.operating_years,
          capex: 0,
          price: 0,
          fixed: 0,
          other: 0,
        });
        setInitialError("");
      })
      .catch((e) => {
        if (e.name !== "AbortError") setInitialError(e.message);
      });
    return () => controller.abort();
  }, [retry]);
  const payload = useMemo(() => {
    if (!base) return null;
    const feed =
      base.financial.feedstock_opex_usd_per_year * (1 + controls.feed / 100);
    const utility =
      base.financial.utility_opex_usd_per_year * (1 + controls.utility / 100);
    return {
      ...base,
      costing: {
        ...base.costing,
        settings: {
          ...base.costing.settings,
          capital_cost_multiplier:
            (base.costing.settings.capital_cost_multiplier ?? 1) *
            (1 + (controls.capex ?? 0) / 100),
        },
      },
      advisor_context: {
        ...(base.advisor_context ?? defaultContext),
        raw_materials: (base.advisor_context?.raw_materials ?? []).map((x) => ({
          ...x,
          annual_cost: x.annual_cost * (1 + controls.feed / 100),
        })),
        utilities: (base.advisor_context?.utilities ?? []).map((x) => ({
          ...x,
          annual_cost: x.annual_cost * (1 + controls.utility / 100),
        })),
      },
      financial: {
        ...base.financial,
        fixed_opex_usd_per_year:
          base.financial.fixed_opex_usd_per_year *
          (1 + (controls.fixed ?? 0) / 100),
        product_selling_price_usd_per_unit:
          base.financial.product_selling_price_usd_per_unit *
          (1 + (controls.price ?? 0) / 100),
        discount_rate: controls.discount / 100,
        operating_years: controls.life,
        feedstock_opex_usd_per_year: feed,
        utility_opex_usd_per_year: utility,
        variable_opex_usd_per_year:
          Math.max(
            0,
            base.financial.variable_opex_usd_per_year -
              base.financial.feedstock_opex_usd_per_year -
              base.financial.utility_opex_usd_per_year,
          ) *
            (1 + (controls.other ?? 0) / 100) +
          feed +
          utility,
      },
    };
  }, [base, controls]);
  const signature = JSON.stringify(payload);
  useEffect(() => {
    if (!payload) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      apiFetch("/api/assessment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: signature,
        signal: controller.signal,
      })
        .then(async (r) => {
          if (!r.ok) throw new Error(await apiError(r));
          return r.json();
        })
        .then((data: Assessment) => {
          setEnvelope({ signature, data });
          setFailure(null);
        })
        .catch((e) => {
          if (e.name !== "AbortError")
            setFailure({ signature, message: e.message });
        });
    }, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [payload, signature]);
  const workspace = useMemo(
    () =>
      payload
        ? { project: payload, streams, native_import: nativeImport }
        : null,
    [payload, streams, nativeImport],
  );
  useEffect(() => {
    if (workspace) writeWorkspace(workspace);
  }, [workspace]);
  function loadWorkspace(w: Workspace) {
    setBase(w.project);
    setStreams(w.streams || []);
    setNativeImport(w.native_import || null);
    setControls({
      feed: 0,
      utility: 0,
      discount: w.project.financial.discount_rate * 100,
      life: w.project.financial.operating_years,
      capex: 0,
      price: 0,
      fixed: 0,
      other: 0,
    });
    setNotice("Saved project version loaded.");
  }
  const data = envelope?.data;
  const error =
    failure?.signature === signature ? failure.message : initialError;
  const updating = !data || envelope?.signature !== signature;
  const ready = !!data && !updating && !error;
  const risk = data?.uncertainty;

  function changeEquipment(index: number, update: Partial<EquipmentSpec>) {
    setBase((prev) =>
      prev
        ? {
            ...prev,
            costing: {
              ...prev.costing,
              equipment: prev.costing.equipment.map((e, i) =>
                i === index ? ({ ...e, ...update } as EquipmentSpec) : e,
              ),
            },
          }
        : prev,
    );
  }
  function addEquipment() {
    if (!base) return;
    let index = base.costing.equipment.length + 1;
    while (base.costing.equipment.some((e) => e.unit_id === `U${index}`))
      index++;
    const unit = {
      ...(kind === "quoted"
        ? { source: "User-provided estimate; verify scope" }
        : {}),
      unit_id: `U${index}`,
      kind,
      material: "carbon_steel",
      quantity: 1,
      ...defaults[kind],
    };
    setBase({
      ...base,
      costing: {
        ...base.costing,
        equipment: [...base.costing.equipment, unit],
      },
    });
    setExpanded(unit.unit_id);
  }
  function updateFinancial(key: string, value: number) {
    setBase((prev) =>
      prev ? { ...prev, financial: { ...prev.financial, [key]: value } } : prev,
    );
  }
  function updateExpense(
    key: "feedstock_opex_usd_per_year" | "utility_opex_usd_per_year" | "other",
    value: number,
  ) {
    setBase((prev) => {
      if (!prev) return prev;
      const f = prev.financial;
      const other = Math.max(
        0,
        f.variable_opex_usd_per_year -
          f.feedstock_opex_usd_per_year -
          f.utility_opex_usd_per_year,
      );
      const feed =
        key === "feedstock_opex_usd_per_year"
          ? value
          : f.feedstock_opex_usd_per_year;
      const utility =
        key === "utility_opex_usd_per_year"
          ? value
          : f.utility_opex_usd_per_year;
      return {
        ...prev,
        financial: {
          ...f,
          feedstock_opex_usd_per_year: feed,
          utility_opex_usd_per_year: utility,
          variable_opex_usd_per_year:
            feed + utility + (key === "other" ? value : other),
        },
      };
    });
  }
  function stressTarget(r: Suggestion) {
    const key = (
      {
        feedstock: "feed",
        utility: "utility",
        capex: "capex",
        selling_price: "price",
        fixed_opex: "fixed",
        other_opex: "other",
      } as const
    )[
      r.parameter as
        | "feedstock"
        | "utility"
        | "capex"
        | "selling_price"
        | "fixed_opex"
        | "other_opex"
    ];
    if (!key) return null;
    const value =
      Math.round(
        ((1 + (controls[key] ?? 0) / 100) * (1 + r.suggested_change_pct / 100) -
          1) *
          1000000,
      ) / 10000;
    if (value < -50 || value > 50) return null;
    if (
      key === "capex" &&
      base &&
      ((base.costing.settings.capital_cost_multiplier ?? 1) *
        (1 + value / 100) >
        1.5 ||
        (base.costing.settings.capital_cost_multiplier ?? 1) *
          (1 + value / 100) <
          0.5)
    )
      return null;
    return { key, value };
  }
  function applyStress(r: Suggestion) {
    const target = stressTarget(r);
    if (!target) return;
    setControls((c) => ({ ...c, [target.key]: target.value }));
    setNotice(
      `Applied ${r.parameter.replaceAll("_", " ")} ${r.suggested_change_pct > 0 ? "+" : ""}${r.suggested_change_pct}% to the current scenario (${r.scope}).`,
    );
  }
  async function upload(file: File) {
    if (!/\.(csv|json|dwxml)$/i.test(file.name)) {
      setUploadMessage(
        "Choose a CSV, JSON, BioSTEAM snapshot or native DWSIM .dwxml file.",
      );
      return;
    }
    if (file.size > 4 * 1024 * 1024) {
      setUploadMessage("The file exceeds the 4 MiB dashboard upload limit.");
      return;
    }
    setUploading(true);
    setUploadMessage("");
    try {
      let response: Response;
      if (/\.dwxml$/i.test(file.name)) {
        const form = new FormData();
        form.append("file", file);
        const r = await apiFetch("/api/streams/parse/dwxml", {
          method: "POST",
          body: form,
        });
        if (!r.ok) throw Error(await apiError(r));
        const imported = (await r.json()) as NativeImport;
        setNativeImport(imported);
        setStreams(imported.streams);
        setFilename(file.name);
        if (base && imported.equipment.length) {
          const costing = { ...base.costing, equipment: imported.equipment };
          const check = await apiFetch("/api/costing/bom", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(costing),
          });
          if (check.ok) {
            setBase({
              ...base,
              costing,
              engineering_notes: importScopeNotes(imported, imported.equipment),
            });
            setUploadMessage(
              `Imported ${imported.streams.length} streams and ${imported.equipment.length} equipment estimates. Financial assumptions retained. Review excluded units and design basis below.`,
            );
          } else
            setUploadMessage(
              `Streams and topology imported. BOM not replaced: ${await apiError(check)}. Review mapping below.`,
            );
        } else
          setUploadMessage(
            "Streams and topology imported; no complete supported sizing found. Complete equipment mapping below. Existing financial assumptions and BOM retained.",
          );
        return;
      }
      if (/\.json$/i.test(file.name)) {
        let content = JSON.parse(await file.text());
        if (content.schema_version === "flowvalue-biosteam-v1") {
          const r = await apiFetch("/api/integrations/biosteam/import", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(content),
          });
          if (!r.ok) throw Error(await apiError(r));
          content = await r.json();
        }
        if (content.costing && content.financial) {
          const validation = await apiFetch("/api/assessment", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(
              Object.fromEntries(
                Object.entries(content).filter(([key]) => key !== "streams"),
              ),
            ),
          });
          if (!validation.ok) throw new Error(await apiError(validation));
          const canonical = await validation.json();
          const financial = { ...canonical.financial.inputs };
          delete financial.total_capex_usd;
          let importedStreams: Stream[] = [];
          if (content.streams?.length) {
            const streamResponse = await apiFetch("/api/streams/parse/json", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ streams: content.streams }),
            });
            if (!streamResponse.ok)
              throw new Error(await apiError(streamResponse));
            importedStreams = (await streamResponse.json()).streams;
          }
          setBase({
            engineering_notes: content.engineering_notes || [],
            financial,
            costing: {
              ...content.costing,
              settings: {
                ...canonical.bom.settings,
                capital_cost_multiplier: 1,
              },
            },
            simulation: content.simulation ?? {
              iterations: 1000,
              variation_fraction: 0.2,
              seed: 42,
            },
            is_demo: content.is_demo ?? false,
            advisor_context: {
              ...defaultContext,
              name: file.name.replace(/\.json$/i, ""),
              ...content.advisor_context,
            },
          });
          setControls({
            feed: 0,
            utility: 0,
            discount: financial.discount_rate * 100,
            life: financial.operating_years,
            capex: (canonical.bom.settings.capital_cost_multiplier - 1) * 100,
            price: 0,
            fixed: 0,
            other: 0,
          });
          setNativeImport(null);
          setStreams(importedStreams);
          setFilename(file.name);
          setUploadMessage(
            "Project loaded and validated. Advisor recommendations now use this project's economics.",
          );
          return;
        }
        response = await apiFetch("/api/streams/parse/json", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(content),
        });
      } else {
        const form = new FormData();
        form.append("file", file);
        response = await apiFetch("/api/streams/parse/csv", {
          method: "POST",
          body: form,
        });
      }
      if (!response.ok) throw new Error(await apiError(response));
      const table = await response.json();
      setNativeImport(null);
      setStreams(table.streams);
      setFilename(file.name);
      setUploadMessage(
        `${table.streams.length} streams validated. Configure equipment sizing below; costs are not inferred from stream data.`,
      );
    } catch (e) {
      setUploadMessage(
        e instanceof Error ? e.message : "Unable to parse the file.",
      );
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }
  async function download(format: "excel" | "pdf") {
    if (!ready || !payload) return;
    setExporting(format);
    setNotice("");
    try {
      const response = await apiFetch(`/api/export/${format}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error(await apiError(response));
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `flowvalue-assessment.${format === "excel" ? "xlsx" : "pdf"}`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setNotice(
        `${format === "excel" ? "Excel model" : "Executive summary"} downloaded for the current scenario.`,
      );
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Download failed.");
    } finally {
      setExporting("");
    }
  }
  const warnings = [
    ...new Set([
      ...(data?.financial.warnings ?? []),
      ...(risk?.warnings ?? []),
      ...(data?.bom.items.flatMap((x) => x.warnings) ?? []),
    ]),
  ];

  if (!base && initialError.startsWith("Sign in"))
    return (
      <main className="auth-screen">
        <a className="auth-brand" href="/dashboard">
          <Waves size={26} /> flowvalue AI
        </a>
        <div className="eyebrow">PROCESS ECONOMICS WORKSPACE</div>
        <h1>
          Bring your process.
          <br />
          Explore its potential.
        </h1>
        <p>
          Sign in to size equipment, explore project economics, and keep a
          private history of your assessments.
        </p>
        <ProjectAccount
          workspace={null}
          onLoad={loadWorkspace}
          onAuth={authChanged}
        />
        <small>
          Engineering calculations are protected by your account. Your projects
          are visible only to you.
        </small>
      </main>
    );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/dashboard">
          <span className="brand-mark">
            <Waves size={23} />
          </span>
          <span>
            flowvalue<span className="brand-ai"> AI</span>
          </span>
        </a>
        <div className="workspace-label">WORKSPACE</div>
        <div className="workspace-switch">
          <span className="workspace-icon">
            <FlaskConical size={17} />
          </span>
          <div>
            <strong>{base?.advisor_context?.name ?? "Untitled process"}</strong>
            <small>Process economics</small>
          </div>
          <ChevronDown size={14} />
        </div>
        <div className="nav-caption">ANALYSIS</div>
        <nav>
          <a href="/process-flow">
            <Layers3 size={18} />
            Interactive process flow
          </a>
          <a href="#overview" className="nav-selected">
            <LayoutDashboard size={18} />
            Overview
            <span className="nav-dot" />
          </a>
          <a href="#equipment">
            <Layers3 size={18} />
            Equipment & costing
          </a>
          <a href="#playground">
            <SlidersHorizontal size={18} />
            Financial playground
          </a>
          <a href="#risk">
            <ShieldCheck size={18} />
            Risk & uncertainty
          </a>
          <a href="#streams">
            <Upload size={18} />
            Simulation data
          </a>
        </nav>
        <div className="sidebar-note">
          <Activity size={18} />
          <strong>From process to possibility.</strong>
          <p>Explore the economics behind your next engineering decision.</p>
          <span>
            <i /> ENGINEERING WORKSPACE
          </span>
        </div>
        <div className="sidebar-bottom">
          <span className="avatar">FV</span>
          <div>
            <strong>Engineering workspace</strong>
            <small>FlowValue AI · v0.1</small>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <span>Techno-economic assessment</span>
          </div>
          <div className="top-actions">
            <span className={`connection ${error ? "connection-error" : ""}`}>
              <i />
              {error
                ? "Needs attention"
                : ready
                  ? "API connected"
                  : "Connecting"}
            </span>
            <button
              className="icon-button"
              aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
              onClick={() => setDark((v) => !v)}
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <span className="top-avatar">FV</span>
          </div>
        </header>
        <main className="dashboard-main" id="overview">
          <ProjectAccount
            workspace={workspace}
            onLoad={loadWorkspace}
            onAuth={authChanged}
          />
          <section className="page-heading">
            <div>
              <div className="eyebrow">
                <span /> PROCESS ECONOMICS PLAYGROUND
              </div>
              <h1>See the value in your process.</h1>
              <p>
                From equipment costs to investment returns. One connected view.
              </p>
            </div>
            <div className="export-actions">
              <Button
                variant="outline"
                className="export-button"
                disabled={!ready || !!exporting}
                onClick={() => download("pdf")}
              >
                {exporting === "pdf" ? (
                  <LoaderCircle className="spin" />
                ) : (
                  <ArrowDownToLine />
                )}
                Executive PDF
              </Button>
              <Button
                className="export-button primary-button"
                disabled={!ready || !!exporting}
                onClick={() => download("excel")}
              >
                {exporting === "excel" ? (
                  <LoaderCircle className="spin" />
                ) : (
                  <FileSpreadsheet />
                )}
                Download Excel
              </Button>
            </div>
          </section>
          {base?.engineering_notes?.some((n) => n.startsWith("INCOMPLETE")) && (
            <div role="alert" className="engineering-warning">
              {base.engineering_notes.find((n) => n.startsWith("INCOMPLETE"))}
            </div>
          )}
          <div className="scenario-bar">
            <div>
              <span className="scenario-badge">
                {base?.is_demo !== false ? "DEMO SCENARIO" : "CURRENT SCENARIO"}
              </span>
              <strong>
                {base?.advisor_context?.name ?? "Untitled process"}
              </strong>
              <span className="scenario-description">
                {base?.is_demo !== false
                  ? "Synthetic equipment & economics · USD"
                  : "User-configured equipment & economics · USD"}
              </span>
            </div>
            <button
              onClick={() => {
                sessionStorage.removeItem(workspaceKey);
                setBase(null);
                setEnvelope(null);
                setStreams([]);
                setNativeImport(null);
                setFilename("");
                setRetry((x) => x + 1);
                setNotice("");
              }}
              className="text-button"
            >
              <RotateCcw size={13} />
              Reset demo
            </button>
          </div>
          {error && (
            <div className="error-banner" role="alert">
              <CircleHelp size={18} />
              <div>
                <strong>Assessment needs attention</strong>
                <p>{error}</p>
              </div>
              {initialError && (
                <button onClick={() => setRetry((x) => x + 1)}>Retry</button>
              )}
            </div>
          )}
          {notice && (
            <div className="notice-banner" role="status">
              <Check size={17} />
              {notice}
              <button
                aria-label="Dismiss notification"
                onClick={() => setNotice("")}
              >
                <X size={15} />
              </button>
            </div>
          )}
          <section
            className={`metric-grid ${updating && data ? "is-updating" : ""}`}
            aria-label="Financial metrics"
            aria-busy={updating}
          >
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
                <small>at {controls.discount}% discount</small>
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">
                Internal rate of return <Activity size={17} />
              </div>
              <strong
                data-testid="irr"
                className={
                  data?.financial.irr === null ? "metric-text" : undefined
                }
              >
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
                Discounted payback <RotateCcw size={17} />
              </div>
              <strong
                data-testid="payback"
                className={
                  data?.financial.discounted_payback_years === null
                    ? "metric-text"
                    : undefined
                }
              >
                {data ? (
                  data.financial.discounted_payback_years === null ? (
                    "Not recovered"
                  ) : (
                    <>
                      {data.financial.discounted_payback_years.toFixed(1)}{" "}
                      <em>years</em>
                    </>
                  )
                ) : (
                  "—"
                )}
              </strong>
              <div className="metric-footer">
                <span>Time to recover CAPEX</span>
                <small>Discounted basis</small>
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
          </section>
          <UniversalAdvisor
            project={payload}
            streams={streams}
            ready={ready}
            context={base?.advisor_context ?? defaultContext}
            onContext={(context) =>
              setBase((prev) =>
                prev ? { ...prev, advisor_context: context } : prev,
              )
            }
            onApply={applyStress}
            canApply={(r) => stressTarget(r) !== null}
          />
          <div className="primary-grid">
            <section className="panel cash-panel">
              <div className="panel-heading">
                <div>
                  <h2>
                    {chartView === "waterfall"
                      ? "Annual cash-flow waterfall"
                      : "Cumulative cash flow"}
                  </h2>
                  <p>The long view on your process economics.</p>
                </div>
                <div className="chart-view-control">
                  <select
                    aria-label="Cash flow chart view"
                    value={chartView}
                    onChange={(e) =>
                      setChartView(e.target.value as "cumulative" | "waterfall")
                    }
                  >
                    <option value="cumulative">Cumulative curve</option>
                    <option value="waterfall">Cash-flow waterfall</option>
                  </select>
                  <span className="quiet-badge">
                    {controls.life}-year horizon
                  </span>
                </div>
              </div>
              <div className="line-legend">
                <span>
                  <i />
                  {chartView === "waterfall"
                    ? "Operating cash flow"
                    : "Undiscounted"}
                </span>
                <span>
                  <i className="gold" />
                  {chartView === "waterfall"
                    ? "Initial investment"
                    : "Discounted"}
                </span>
                <span className="calculation-status" role="status">
                  {error ? (
                    "Check inputs"
                  ) : updating ? (
                    <>
                      <LoaderCircle size={12} className="spin" />
                      Recalculating
                    </>
                  ) : (
                    <>
                      <Check size={12} />
                      Up to date
                    </>
                  )}
                </span>
              </div>
              <div className="chart-area">
                {data ? (
                  <CashFlowChart data={data} view={chartView} />
                ) : (
                  <div className="chart-placeholder">
                    <LoaderCircle className="spin" />
                    Connecting to the financial engine
                  </div>
                )}
              </div>
              <div className="chart-bottom">
                <span>Initial investment</span>
                <strong>
                  {data ? usd(data.bom.total_bare_module_cost_usd) : "—"}
                </strong>
                <span className="chart-bottom-note">CAPEX at year zero</span>
              </div>
            </section>
            <section className="panel playground-panel" id="playground">
              <div className="panel-heading">
                <div>
                  <span className="section-icon">
                    <SlidersHorizontal size={17} />
                  </span>
                  <h2>Financial playground</h2>
                  <p>Adjust an assumption. See the impact.</p>
                </div>
              </div>
              <RangeControl
                label="Feedstock price"
                value={controls.feed}
                min={-50}
                max={50}
                unit="%"
                change={(v) => setControls((c) => ({ ...c, feed: v }))}
                detail={
                  payload
                    ? `${usd(payload.financial.feedstock_opex_usd_per_year)}/year at fixed consumption`
                    : "Annual feedstock cost"
                }
              />
              <RangeControl
                label="Utility rates"
                value={controls.utility}
                min={-50}
                max={50}
                unit="%"
                change={(v) => setControls((c) => ({ ...c, utility: v }))}
                detail={
                  payload
                    ? `${usd(payload.financial.utility_opex_usd_per_year)}/year at fixed consumption`
                    : "Annual utility cost"
                }
              />
              <details className="additional-stresses">
                <summary>Capital, price & other sensitivities</summary>
                <RangeControl
                  label="CAPEX stress"
                  value={controls.capex ?? 0}
                  min={-50}
                  max={50}
                  step={0.1}
                  unit="%"
                  change={(v) => setControls((c) => ({ ...c, capex: v }))}
                  detail="Scales purchased and bare module costs; retained in exports"
                />
                <RangeControl
                  label="Selling price stress"
                  value={controls.price ?? 0}
                  min={-50}
                  max={50}
                  step={0.1}
                  unit="%"
                  change={(v) => setControls((c) => ({ ...c, price: v }))}
                  detail={
                    payload
                      ? `$${payload.financial.product_selling_price_usd_per_unit.toFixed(2)} per product unit`
                      : "Product price at fixed output"
                  }
                />
                <RangeControl
                  label="Fixed OPEX stress"
                  value={controls.fixed ?? 0}
                  min={-50}
                  max={50}
                  step={0.1}
                  unit="%"
                  change={(v) => setControls((c) => ({ ...c, fixed: v }))}
                  detail="Annual fixed operating cost"
                />
                <RangeControl
                  label="Other variable OPEX stress"
                  value={controls.other ?? 0}
                  min={-50}
                  max={50}
                  step={0.1}
                  unit="%"
                  change={(v) => setControls((c) => ({ ...c, other: v }))}
                  detail="Excludes raw materials and utilities"
                />
              </details>
              <RangeControl
                label="Discount rate"
                value={controls.discount}
                min={0}
                max={30}
                step={0.5}
                unit="%"
                change={(v) => setControls((c) => ({ ...c, discount: v }))}
                detail="Annual investment hurdle rate"
              />
              <RangeControl
                label="Plant life"
                value={controls.life}
                min={1}
                max={50}
                unit=" yr"
                change={(v) => setControls((c) => ({ ...c, life: v }))}
                detail="Operating years after the initial investment"
              />
            </section>
          </div>
          <div className="secondary-grid">
            <section className="panel" id="risk">
              <div className="panel-heading">
                <div>
                  <h2>Every outcome, considered.</h2>
                  <p>
                    NPV distribution from{" "}
                    {risk?.iterations.toLocaleString() ?? "1,000"} Monte Carlo
                    scenarios.
                  </p>
                </div>
                <span className="quiet-badge">±20% cost risk</span>
              </div>
              <div className="risk-chart">
                {data ? (
                  <RiskChart data={data} />
                ) : (
                  <div className="chart-placeholder">
                    Waiting for the risk engine
                  </div>
                )}
              </div>
              <div className="percentile-grid">
                {[
                  ["P10 · lower", risk?.p10_npv_usd],
                  ["P50 · median", risk?.p50_npv_usd],
                  ["P90 · upper", risk?.p90_npv_usd],
                ].map(([label, value]) => (
                  <div key={label}>
                    <span>{label}</span>
                    <strong>
                      {typeof value === "number" ? usd(value, true) : "—"}
                    </strong>
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
              {data ? (
                <CapexChart data={data} />
              ) : (
                <div className="chart-placeholder">
                  Waiting for the costing engine
                </div>
              )}
              <div className="probability-note">
                <ShieldCheck size={17} />
                <span>
                  Positive NPV in{" "}
                  <strong>
                    {risk ? percent(risk.probability_positive_npv) : "—"}
                  </strong>{" "}
                  of simulated scenarios.
                </span>
              </div>
            </section>
          </div>
          <section className="panel equipment-panel" id="equipment">
            <div className="panel-heading">
              <div>
                <h2>
                  Equipment bill of materials{" "}
                  <span className="count-badge">
                    {base?.costing.equipment.length ?? 0}
                  </span>
                </h2>
                <p>
                  Inspect sizing, compare construction materials, and trace
                  every cost.
                </p>
              </div>
              <div className="add-equipment">
                <select
                  aria-label="Equipment type to add"
                  value={kind}
                  onChange={(e) => setKind(e.target.value as Kind)}
                >
                  {Object.entries(kindLabels).map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </select>
                <Button
                  variant="outline"
                  disabled={!base}
                  onClick={addEquipment}
                >
                  <Plus size={14} />
                  Add unit
                </Button>
              </div>
            </div>
            <div className="table-scroll">
              <table className="bom-table">
                <thead>
                  <tr>
                    <th>Equipment</th>
                    <th>Design size / unit</th>
                    <th>Material of construction</th>
                    <th>Qty</th>
                    <th>Purchased / unit</th>
                    <th>Bare module total</th>
                    <th>
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {base?.costing.equipment.map((spec, index) => {
                    const item = data?.bom.items.find(
                      (x) => x.unit_id === spec.unit_id,
                    );
                    const open = expanded === spec.unit_id;
                    return (
                      <Fragment key={`${index}-${spec.unit_id}`}>
                        <tr>
                          <td>
                            <button
                              className="equipment-name"
                              aria-expanded={open}
                              onClick={() =>
                                setExpanded(open ? null : spec.unit_id)
                              }
                            >
                              {open ? (
                                <ChevronDown size={14} />
                              ) : (
                                <ChevronRight size={14} />
                              )}
                              <span className="equipment-symbol">
                                {spec.kind === "heat_exchanger" ? (
                                  <Waves size={17} />
                                ) : spec.kind === "pump" ||
                                  spec.kind === "compressor" ? (
                                  <Activity size={17} />
                                ) : (
                                  <FlaskConical size={17} />
                                )}
                              </span>
                              <span>
                                <strong>{spec.unit_id}</strong>
                                <small>{kindLabels[spec.kind]}</small>
                              </span>
                            </button>
                          </td>
                          <td>
                            {item ? (
                              <>
                                {item.correlation_size.toLocaleString("en-US", {
                                  maximumFractionDigits: 1,
                                })}{" "}
                                <span className="cell-unit">
                                  {item.correlation_size_unit}
                                </span>
                              </>
                            ) : (
                              "Pending"
                            )}
                          </td>
                          <td>
                            <select
                              aria-label={`${spec.unit_id} material`}
                              value={spec.material ?? "carbon_steel"}
                              onChange={(e) =>
                                changeEquipment(index, {
                                  material: e.target.value,
                                })
                              }
                            >
                              <option value="carbon_steel">Carbon steel</option>
                              <option value="stainless_steel">
                                Stainless steel
                              </option>
                            </select>
                          </td>
                          <td>
                            <input
                              className="quantity-input"
                              type="number"
                              min={1}
                              max={10000}
                              aria-label={`${spec.unit_id} quantity`}
                              value={spec.quantity ?? 1}
                              onChange={(e) =>
                                changeEquipment(index, {
                                  quantity: Number(e.target.value),
                                })
                              }
                            />
                          </td>
                          <td>
                            {item
                              ? usd(item.purchased_equipment_cost_usd)
                              : "—"}
                          </td>
                          <td className="cost-cell">
                            {item
                              ? usd(item.bare_module_cost_usd * item.quantity)
                              : "—"}
                          </td>
                          <td>
                            <button
                              className="icon-button remove-unit"
                              aria-label={`Remove ${spec.unit_id}`}
                              disabled={
                                (base?.costing.equipment.length ?? 0) <= 1
                              }
                              onClick={() =>
                                setBase((prev) =>
                                  prev
                                    ? {
                                        ...prev,
                                        costing: {
                                          ...prev.costing,
                                          equipment:
                                            prev.costing.equipment.filter(
                                              (_, i) => i !== index,
                                            ),
                                        },
                                      }
                                    : prev,
                                )
                              }
                            >
                              <Trash2 size={14} />
                            </button>
                          </td>
                        </tr>
                        {open && (
                          <tr className="equipment-detail">
                            <td colSpan={7}>
                              <div className="detail-label">
                                <Settings2 size={14} />
                                Per-unit sizing inputs
                              </div>
                              {spec.kind === "quoted" && (
                                <p className="factor-note">
                                  Source:{" "}
                                  {String(
                                    spec.source ||
                                      "User estimate; verify provenance",
                                  )}
                                </p>
                              )}
                              <div className="equipment-fields">
                                {Object.entries(defaults[spec.kind]).map(
                                  ([key, value]) => (
                                    <NumberField
                                      key={key}
                                      label={fieldLabels[key]}
                                      value={Number(spec[key] ?? value)}
                                      change={(v) =>
                                        changeEquipment(index, { [key]: v })
                                      }
                                    />
                                  ),
                                )}
                              </div>
                              {item && (
                                <div className="sizing-output">
                                  {Object.entries(item.sizing).map(
                                    ([key, value]) => (
                                      <span key={key}>
                                        {key.replaceAll("_", " ")}:{" "}
                                        <strong>
                                          {value.toLocaleString("en-US", {
                                            maximumFractionDigits: 3,
                                          })}
                                        </strong>
                                      </span>
                                    ),
                                  )}
                                </div>
                              )}
                              <p className="factor-note">
                                {item
                                  ? `Applied factors: Fm ${item.material_factor.toFixed(2)} · Fp ${item.pressure_factor.toFixed(2)}.`
                                  : "Sizing pending."}{" "}
                                Generic stainless cost factors are used;
                                grade-specific strength remains a design input.
                              </p>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan={5}>
                      Total bare module CAPEX{" "}
                      <span>Quantity-weighted · USD</span>
                    </td>
                    <td className="cost-cell">
                      {data ? usd(data.bom.total_bare_module_cost_usd) : "—"}
                    </td>
                    <td />
                  </tr>
                </tfoot>
              </table>
            </div>
            <div className="equipment-footnote">
              <CircleHelp size={14} />
              <span>
                Per-unit costs include material, pressure and CEPCI adjustments.
                Offsites, contingency and owner costs are excluded.
              </span>
            </div>
          </section>
          <div className="bottom-grid">
            <section className="panel upload-panel" id="streams">
              <div className="panel-heading">
                <div>
                  <h2>Bring your process data</h2>
                  <p>
                    Import CSV, JSON, a BioSTEAM snapshot, or a native DWSIM
                    .dwxml simulation.
                  </p>
                </div>
                <Upload size={18} className="muted-icon" />
              </div>
              <input
                ref={fileRef}
                className="sr-only"
                type="file"
                accept=".csv,.json,.dwxml"
                aria-label="Upload stream table"
                onChange={(e) => {
                  if (e.target.files?.[0]) upload(e.target.files[0]);
                }}
              />
              <button
                className={`dropzone ${dragging ? "dragging" : ""}`}
                disabled={uploading}
                onClick={() => fileRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragging(false);
                  if (e.dataTransfer.files[0]) upload(e.dataTransfer.files[0]);
                }}
              >
                <span className="upload-icon">
                  {uploading ? (
                    <LoaderCircle size={21} className="spin" />
                  ) : (
                    <Upload size={21} />
                  )}
                </span>
                <strong>
                  {filename || "Drop a stream table or project here"}
                </strong>
                <span>
                  or <b>browse files</b> · CSV, JSON or DWXML · up to 4 MiB
                </span>
              </button>
              <p className="upload-message" role="status">
                {uploadMessage ||
                  "Streams: stream_id, mass_flow_kg_h, temperature_c, pressure_bar_abs, phase. Project JSON: costing, financial, and optional advisor_context."}
              </p>
              {streams.length > 0 && (
                <details className="stream-details">
                  <summary>
                    {streams.length} validated streams <ChevronDown size={12} />
                  </summary>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Stream</th>
                          <th>kg/h</th>
                          <th>°C</th>
                          <th>bar abs</th>
                          <th>Phase</th>
                        </tr>
                      </thead>
                      <tbody>
                        {streams.slice(0, 100).map((s) => (
                          <tr key={s.stream_id}>
                            <td>{s.stream_id}</td>
                            <td>{s.mass_flow_kg_h}</td>
                            <td>{s.temperature_c}</td>
                            <td>{s.pressure_bar_abs}</td>
                            <td>{s.phase}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {streams.length > 100 && (
                    <p>Showing the first 100 streams.</p>
                  )}
                </details>
              )}
            </section>
            <section className="panel assumptions-panel">
              <div className="panel-heading">
                <div>
                  <h2>Make the assumptions yours</h2>
                  <p>Annual values at the selected capacity factor.</p>
                </div>
                <Settings2 size={18} className="muted-icon" />
              </div>
              {base && (
                <>
                  <div className="assumption-fields">
                    <NumberField
                      label="Selling price · USD/unit"
                      value={base.financial.product_selling_price_usd_per_unit}
                      change={(v) =>
                        updateFinancial("product_selling_price_usd_per_unit", v)
                      }
                    />
                    <NumberField
                      label="Plant capacity · units/year"
                      value={base.financial.plant_capacity_units_per_year}
                      change={(v) =>
                        updateFinancial("plant_capacity_units_per_year", v)
                      }
                    />
                    <NumberField
                      label="Fixed OPEX · USD/year"
                      value={base.financial.fixed_opex_usd_per_year}
                      change={(v) =>
                        updateFinancial("fixed_opex_usd_per_year", v)
                      }
                    />
                    <NumberField
                      label="Base feedstock · USD/year"
                      value={base.financial.feedstock_opex_usd_per_year}
                      change={(v) =>
                        updateExpense("feedstock_opex_usd_per_year", v)
                      }
                    />
                    <NumberField
                      label="Base utilities · USD/year"
                      value={base.financial.utility_opex_usd_per_year}
                      change={(v) =>
                        updateExpense("utility_opex_usd_per_year", v)
                      }
                    />
                    <NumberField
                      label="Other variable OPEX · USD/year"
                      value={Math.max(
                        0,
                        base.financial.variable_opex_usd_per_year -
                          base.financial.feedstock_opex_usd_per_year -
                          base.financial.utility_opex_usd_per_year,
                      )}
                      change={(v) => updateExpense("other", v)}
                    />
                    <NumberField
                      label="Tax rate · %"
                      value={base.financial.tax_rate * 100}
                      change={(v) => updateFinancial("tax_rate", v / 100)}
                    />
                    <NumberField
                      label="Target CEPCI"
                      value={base.costing.settings.cepci_current}
                      change={(v) =>
                        setBase({
                          ...base,
                          costing: {
                            ...base.costing,
                            settings: {
                              ...base.costing.settings,
                              cepci_current: v,
                            },
                          },
                        })
                      }
                    />
                    <NumberField
                      label="Capacity factor · %"
                      value={base.financial.capacity_factor * 100}
                      change={(v) =>
                        updateFinancial("capacity_factor", v / 100)
                      }
                    />
                  </div>
                  <label className="extrapolation-control">
                    <input
                      type="checkbox"
                      checked={base.is_demo}
                      onChange={(e) =>
                        setBase({ ...base, is_demo: e.target.checked })
                      }
                    />
                    Label exports as a demonstration
                  </label>
                  <label className="extrapolation-control">
                    <input
                      type="checkbox"
                      checked={base.costing.settings.allow_extrapolation}
                      onChange={(e) =>
                        setBase({
                          ...base,
                          costing: {
                            ...base.costing,
                            settings: {
                              ...base.costing.settings,
                              allow_extrapolation: e.target.checked,
                            },
                          },
                        })
                      }
                    />
                    Allow flagged correlation extrapolation
                  </label>
                </>
              )}
              <p className="model-basis">
                Straight-line depreciation · No loss carryforward · Explicit
                incentive scenarios
                <br />
                CEPCI 800 / 397 is a configurable planning basis.
              </p>
            </section>
          </div>
          <details className="basis-details">
            <summary>
              <ShieldCheck size={15} />
              Calculation basis & engineering notes{" "}
              <span>{warnings.length} notes</span>
              <ChevronDown size={14} />
            </summary>
            <div>
              <p>
                Preliminary screening estimates using Turton module
                correlations. Reactor costs cover vessel shells. Compressor
                sizing assumes a single-stage ideal gas. Uploaded stream data
                does not automatically size equipment.
              </p>
              {warnings.map((w, i) => (
                <p key={i}>{w}</p>
              ))}
              <p>
                Risk scenarios use independent uniform feedstock and utility
                multipliers, held constant over each project life. P10, P50 and
                P90 are ascending NPV percentiles. Depreciation life defaults to
                operating life.
              </p>
            </div>
          </details>
          {base && payload && (
            <EngineeringTools
              project={base}
              scenario={payload}
              ready={ready}
              onProject={setBase}
              native={nativeImport}
              onNative={setNativeImport}
            />
          )}
          <footer className="dashboard-footer">
            <span>
              <Waves size={15} />
              FlowValue AI
            </span>
            <p>Transparent calculations. Better engineering decisions.</p>
            <a href="/api/reference" target="_blank" rel="noreferrer">
              API reference
              <ArrowRight size={12} />
            </a>
          </footer>
        </main>
      </div>
    </div>
  );
}
