"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { WorkspaceNavigation } from "@/components/workspace-navigation";
import { StageJourney } from "@/blocks/shared/stage-journey";
import { assessmentFromUrl, assessmentHref } from "@/lib/assessment-navigation";
import "./rate-workspace.css";
import { RevenueMethodForm } from "@/components/revenue-method-form";
import { PriceReview } from "./price-review";

import {
  type Row,
  type IncomeLine,
  object,
  array,
  number,
  amount,
  full,
  revenueLines,
  meceMethods,
  meceFormula,
  requiresTerms,
} from "./rate-lines";
async function api(path: string, options?: RequestInit) {
  const response = await fetch("/api/" + path, {
    ...options,
    cache: "no-store",
  });
  if (response.status === 401) {
    location.assign("/login");
    throw Error("Please sign in");
  }
  const body = await response.json();
  if (!response.ok)
    throw Error(
      typeof body.detail === "string"
        ? body.detail
        : "Check the highlighted revenue inputs",
    );
  return body;
}
const post = (body: unknown) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
const rateUnits = [
  "kg/h",
  "kg/day",
  "kg/min",
  "kg/s",
  "tonne/h",
  "tonne/day",
  "lb/h",
  "m3/h",
  "m3/day",
  "m3/min",
  "L/h",
  "L/min",
  "L/s",
];
export default function RateRevenueWorkspace() {
  const [id, setId] = useState(""),
    [state, setState] = useState<Row | null>(null),
    [lines, setLines] = useState<IncomeLine[]>([]),
    [changed, setChanged] = useState<Set<string>>(new Set()),
    [removed, setRemoved] = useState<string[]>([]),
    [days, setDays] = useState(314),
    [hours, setHours] = useState(24),
    [timeDirty, setTimeDirty] = useState(false),
    [years, setYears] = useState(20),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [panel, setPanel] = useState<"assistant" | "calendar" | string | null>(
      null,
    ),
    [text, setText] = useState(""),
    [dark, setDark] = useState(false);
  const aiEdits = useRef<{
      rows: IncomeLine[];
      fields: Record<string, string[]>;
      removed: string[];
      days: number;
      hours: number;
      years: number;
    } | null>(null),
    fieldEdits = useRef<Record<string, string[]>>({});
  const dirty = useRef(false),
    loaded = useRef(false),
    dialog = useRef<HTMLDivElement>(null),
    close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    setId(
      assessmentFromUrl(
        location.href,
        localStorage.getItem("flowvalue-assessment"),
      ),
    );
    setDark(localStorage.getItem("flowvalue-theme") === "dark");
  }, []);
  function hydrate(next: Row) {
    const config = object(object(next.plan).operating_economics),
      ops = object(config.operating),
      rows = revenueLines(config);
    if (aiEdits.current && next.running) return;
    const held = aiEdits.current;
    if (held) {
      for (const previous of held.rows) {
        const index = rows.findIndex(
          (r) =>
            r.id === previous.id ||
            (r.name && r.name.toLowerCase() === previous.name.toLowerCase()),
        );
        const fields = held.fields[previous.id] || [];
        if (index >= 0) {
          const preserved = Object.fromEntries(
            fields.map((key) => [key, (previous as unknown as Row)[key]]),
          );
          rows[index] = { ...rows[index], ...preserved };
          fieldEdits.current[rows[index].id] = fields;
        } else if (
          previous.name ||
          previous.rate !== null ||
          previous.price !== null
        ) {
          rows.push(previous);
          fieldEdits.current[previous.id] = fields;
        }
      }
      aiEdits.current = null;
    }
    setLines(rows.filter((r) => !held?.removed.includes(r.id)));
    setDays(held?.days ?? number(ops.days_per_year) ?? 314);
    setHours(held?.hours ?? number(ops.hours_per_day) ?? 24);
    setYears(
      held?.years ?? number(object(config.financial).operating_years) ?? 20,
    );
    setText(String(next.revenue_description || ""));
    setChanged(
      new Set([
        ...rows.filter((r) => r.confirmRate).map((r) => r.id),
        ...(held ? Object.keys(fieldEdits.current) : []),
      ]),
    );
    setRemoved(held?.removed || []);
    setTimeDirty(Boolean(held));
    dirty.current = rows.some((r) => r.confirmRate) || Boolean(held);
    if (
      !loaded.current &&
      !next.revenue_approval &&
      object(next.ai).revenue &&
      rows.length
    )
      setPanel("assistant");
    loaded.current = true;
  }
  useEffect(() => {
    if (!id) return;
    let alive = true,
      timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const next = await api("assessments/" + id);
        if (!alive) return;
        setState(next);
        if (!loaded.current || !dirty.current) hydrate(next);
        if (next.running) timer = setTimeout(load, 1000);
      } catch (e) {
        if (alive) setError((e as Error).message);
      }
    }
    void load();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [id, busy]);
  useEffect(() => {
    if (!panel) return;
    const before = document.activeElement as HTMLElement | null,
      overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    close.current?.focus();
    function key(e: KeyboardEvent) {
      if (e.key === "Escape") setPanel(null);
      if (e.key === "Tab") {
        const controls = Array.from(
          dialog.current?.querySelectorAll<HTMLElement>(
            "button,a[href],input,select,textarea,summary",
          ) || [],
        ).filter(
          (n) => n.getClientRects().length && !n.hasAttribute("disabled"),
        );
        if (e.shiftKey && document.activeElement === controls[0]) {
          e.preventDefault();
          controls.at(-1)?.focus();
        } else if (!e.shiftKey && document.activeElement === controls.at(-1)) {
          e.preventDefault();
          controls[0]?.focus();
        }
      }
    }
    window.addEventListener("keydown", key);
    return () => {
      document.body.style.overflow = overflow;
      window.removeEventListener("keydown", key);
      before?.focus();
    };
  }, [panel]);
  const config = object(object(state?.plan).operating_economics),
    fin = object(config.financial),
    basis = object(config.price_basis),
    stages = object(object(state?.results).stages),
    revenueStage = object(stages.revenue),
    result = object(revenueStage.result),
    annual = array(result.annual),
    currency = String(object(result.basis).currency || basis.currency || "USD"),
    streams = array(
      object(
        state?.scoped_report ||
          state?.effective_report ||
          object(state?.parsed).report,
      ).entities,
    ).filter((e) => e.kind === "material"),
    pending = array(config.pending_inputs),
    construction = Number(fin.construction_years || 0),
    life = Number(fin.operating_years || 20),
    active = busy || Boolean(state?.running) || !state,
    isDirty = changed.size > 0 || removed.length > 0 || timeDirty;
  const selected = lines.find((r) => r.id === panel),
    latest = annual.at(-1),
    total =
      annual.length && annual.every((r) => number(r.sales_revenue) !== null)
        ? annual.reduce((n, r) => n + Number(r.sales_revenue), 0)
        : null;
  function patch(key: string, change: Partial<IncomeLine>) {
    fieldEdits.current[key] = [
      ...new Set([...(fieldEdits.current[key] || []), ...Object.keys(change)]),
    ];
    setLines((rows) =>
      rows.map((r) => (r.id === key ? { ...r, ...change } : r)),
    );
    setChanged((ids) => new Set([...ids, key]));
    dirty.current = true;
  }
  function add(kind: "product" | "service", seed?: Row) {
    const key = String(seed?.id || "income-" + crypto.randomUUID());
    setLines((rows) => [
      ...rows,
      {
        id: key,
        name: String(seed?.name || ""),
        kind,
        category: String(
          seed?.category ||
            (kind === "product" ? "product_sales" : "processing_services"),
        ),
        role: "main_product",
        method_form: null,
        stream_key: null,
        component: null,
        rate: null,
        rate_unit: "m3/h",
        price: null,
        price_unit: "m3",
        price_period: String(
          object(object(state?.plan).cost_translation).target_period ||
            new Date().getFullYear(),
        ),
        sold_fraction: 1,
        saleable_fraction: 1,
        allocation_fraction: 1,
        rationale: "Explicit user rate and selling-price planning assumption",
      },
    ]);
    fieldEdits.current[key] = ["kind", ...(seed ? ["name"] : [])];
    setChanged((ids) => new Set([...ids, key]));
    dirty.current = true;
  }
  function sourceFor(line: IncomeLine) {
    const entity = streams.find((s) => s.key === line.stream_key),
      prop =
        (line.component ? "component_" : "") +
        (["m3", "L"].includes(line.price_unit) ? "volume_flow" : "mass_flow");
    return array(entity?.values).find(
      (v) =>
        v.property === prop &&
        (!line.component || v.component === line.component) &&
        number(v.normalized_value) !== null,
    );
  }
  function income(line: IncomeLine) {
    const group = line.kind === "product" ? "products" : "commercial",
      key = line.kind === "product" ? "product_id" : "line_id",
      source = array(result[group]).find(
        (r) => r[key] === line.id && r.year === latest?.year,
      );
    return source?.net_sales_revenue ?? source?.revenue;
  }
  function missing(line: IncomeLine) {
    if (line.method_form) return "";
    if (requiresTerms(line)) return "Payment details";
    return [
      !line.name.trim() ? "Name" : null,
      !line.stream_key && line.rate === null ? "Flow rate" : null,
      line.price === null ? "Price" : null,
    ]
      .filter(Boolean)
      .join(" · ");
  }
  async function persist(approve: boolean) {
    if (!state) return;
    const edits = lines.filter((r) => changed.has(r.id) && !r.advanced);
    const invalid = edits.find((r) =>
      approve
        ? missing(r)
        : missing(r)
            .split(" · ")
            .some((k) => !["Price", "Flow rate", ""].includes(k)),
    );
    if (invalid)
      throw Error(
        (invalid.name || "New income line") + ": enter " + missing(invalid),
      );
    const next = await api(
      `assessments/${id}/revenue-rates`,
      post({
        revision: state.revision,
        lines: edits.map(({ advanced, confirmRate, original, ...r }) => r),
        remove: removed,
        days_per_year: days,
        hours_per_day: hours,
        operating_years: years,
        approve,
      }),
    );
    setState(next);
    dirty.current = false;
    fieldEdits.current = {};
    hydrate(next);
    return next;
  }
  async function save(calculate = false) {
    setBusy(true);
    setError("");
    try {
      await persist(calculate);
      if (calculate)
        await api(
          state?.workflow === "revenue"
            ? `assessments/${id}/run`
            : `assessments/${id}/stages/revenue/run`,
          post({ use_ai: false }),
        );
      setNotice(
        calculate
          ? "Saved and approved. Python is updating the revenue forecast."
          : "Saved. The previous calculation remains available until you recalculate.",
      );
      setPanel(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function interpret() {
    if (!state) return;
    setBusy(true);
    setError("");
    try {
      let description = text;
      if (isDirty) {
        const edited = lines.filter((r) => changed.has(r.id));
        aiEdits.current = {
          rows: edited,
          fields: structuredClone(fieldEdits.current),
          removed: [...removed],
          days,
          hours,
          years,
        };
        description +=
          "\n\nCurrent explicit worksheet edits supersede older assumptions for these entries:\n" +
          edited
            .filter((r) => r.name || r.rate !== null || r.price !== null)
            .map(
              (r) =>
                `User-selected ${r.category || "product_sales"} (${r.role || ""}): ${r.name || "unnamed income"}; ${r.method_form ? JSON.stringify(r.method_form) : r.stream_key ? "stream " + r.stream_key : r.rate === null ? "custom rate not provided" : String(r.rate) + " " + r.rate_unit}; ${r.price === null ? "price not provided" : String(r.price) + " " + String(basis.currency || currency) + "/" + r.price_unit}; price period ${r.price_period || basis.price_period}`,
            )
            .join("\n");
        if (removed.length)
          description += "\nRemove these income ids: " + removed.join(", ");
      }
      const next = await api(
        `assessments/${id}/revenue-authority`,
        post({
          revision: state.revision,
          revenue_description: description,
          reinterpret: true,
        }),
      );
      dirty.current = false;
      setState(next);
      setText(description);
      setPanel("assistant");
      setNotice(
        "AI is drafting income lines. Your explicit worksheet edits are retained for review.",
      );
    } catch (e) {
      aiEdits.current = null;
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function chooseMethod(line: IncomeLine, category: string) {
    patch(line.id, {
      category,
      kind: category === "product_sales" ? "product" : "service",
      method_form: null,
      advanced: false,
      price_review: null,
    });
  }
  async function researchPrice(line: IncomeLine) {
    setBusy(true);
    setError("");
    try {
      const saved =
        !changed.has(line.id) && !timeDirty && !removed.length
          ? state
          : await persist(false);
      if (!saved) return;
      await api(
        `assessments/${id}/research`,
        post({
          revision: saved.revision,
          kind: "market",
          target_id: line.id,
          consent: true,
          recommend_price: true,
          focus:
            "Find comparable dated prices or tariffs for this income method, with grade, location, bulk scale and commercial basis. Recommend a supported observation and explain the observed range.",
        }),
      );
      setNotice(
        "Researching this income line. The saved baseline is unchanged until you accept and calculate.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function researchMissingPrices() {
    if (!state) return;
    setBusy(true);
    setError("");
    try {
      let cursor = isDirty ? await persist(false) : state;
      if (!cursor) return;
      const targets = lines.filter((r) => r.price === null && r.name.trim());
      for (let i = 0; i < targets.length; i++) {
        setNotice(
          `Researching missing prices: ${i + 1} of ${targets.length} · ${targets[i].name}`,
        );
        await api(
          `assessments/${id}/research`,
          post({
            revision: cursor.revision,
            kind: "market",
            target_id: targets[i].id,
            consent: true,
            recommend_price: true,
            focus:
              "Find dated comparable market prices/tariffs with grade, region, volume and commercial basis; recommend an applicable observation with source-backed bounds.",
          }),
        );
        do {
          await new Promise((resolve) => setTimeout(resolve, 1000));
          cursor = await api(`assessments/${id}`);
          setState(cursor);
        } while (cursor.running);
      }
      hydrate(cursor);
      setNotice(
        "Price research finished. Review each sourced proposal and use the ones you accept; no researched price has been applied automatically.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function acceptPrice(line: IncomeLine, proposal: Row) {
    try {
      let change: Partial<IncomeLine> = {
        price: number(proposal.selected),
        price_period: String(proposal.price_period),
        price_review: proposal,
      };
      if (line.method_form) {
        const form = object(line.method_form),
          inputs = {
            ...object(form.inputs),
            [form.subtype === "fixed" ? "fixed" : "rate"]: proposal.selected,
          };
        const built = await api(
          `assessments/${id}/revenue-line-preview`,
          post({
            revision: state?.revision,
            method: line.category,
            subtype: form.subtype,
            inputs,
            identity: line.id,
          }),
        );
        change = {
          ...revenueLines({ commercial_lines: [built] })[0],
          ...change,
        };
      }
      patch(line.id, change);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const ready = lines.filter((r) => !r.advanced && !missing(r)).length,
    maxAnnual = Math.max(1, ...annual.map((r) => Number(r.sales_revenue || 0)));
  const incomeEditor = (
    <>
      <section className="rr-income">
        <div className="rr-section-head">
          <div>
            <h2>Income</h2>
            <p>Choose what earns money, then add a price.</p>
          </div>
          <div>
            {lines.some((r) => r.price === null) && (
              <button
                className="secondary"
                disabled={active}
                onClick={() => void researchMissingPrices()}
              >
                Find missing prices ↗
              </button>
            )}
            <button
              className="secondary"
              disabled={active}
              onClick={() => add("product")}
            >
              + Add product
            </button>
            <button
              className="secondary"
              disabled={active}
              onClick={() =>
                add("service", { category: "other_contractual_income" })
              }
            >
              + Add other income
            </button>
          </div>
        </div>
        {lines.some((r) => r.price === null) && (
          <small className="rr-consent">
            Finding prices uses web research and AI credits. You choose which
            prices to use.
          </small>
        )}
        <details className="rr-time-options">
          <summary>
            Time period · {years} {years === 1 ? "year" : "years"} · {days} days
            a year · {hours} hours a day
          </summary>
          <div className="rr-review-calendar">
            <label>
              Operating years
              <input
                aria-label="Revenue analysis operating years"
                type="number"
                min="1"
                max="50"
                value={years}
                disabled={active}
                onChange={(e) => {
                  setYears(Number(e.target.value));
                  setTimeDirty(true);
                  dirty.current = true;
                }}
              />
            </label>
            <label>
              Days / year
              <input
                aria-label="Review days per year"
                type="number"
                min="1"
                max="366"
                value={days}
                disabled={active}
                onChange={(e) => {
                  setDays(Number(e.target.value));
                  setTimeDirty(true);
                  dirty.current = true;
                }}
              />
            </label>
            <label>
              Hours / day
              <input
                aria-label="Review hours per day"
                type="number"
                min="0.01"
                max="24"
                step="any"
                value={hours}
                disabled={active}
                onChange={(e) => {
                  setHours(Number(e.target.value));
                  setTimeDirty(true);
                  dirty.current = true;
                }}
              />
            </label>
            <p>
              One shared project timeline. Existing production ramp and
              construction timing are retained.{" "}
              <Link href={assessmentHref("/cashflow", id)}>Review ramp ↗</Link>
            </p>
          </div>
        </details>
        {!lines.length && (
          <div className="rr-empty">
            <strong>What earns income?</strong>
            <p>
              Add a product or processing fee, or describe your business to the
              assistant.
            </p>
            <button disabled={active} onClick={() => setPanel("assistant")}>
              Describe income methods →
            </button>
          </div>
        )}
        <div className="rr-line-list">
          {lines.map((line) => {
            const observed = sourceFor(line);
            return (
              <article className="rr-line" key={line.id}>
                <div className="rr-line-top">
                  <span className="rr-tag">
                    {meceMethods[line.category || "product_sales"]}
                  </span>
                  <span>
                    {line.advanced
                      ? "Existing contract · detailed terms"
                      : missing(line) || "Ready"}
                  </span>
                  <button
                    className="secondary"
                    aria-label={`Remove ${line.name || "income source"}`}
                    disabled={active}
                    onClick={() => {
                      setLines((rows) => rows.filter((r) => r.id !== line.id));
                      setRemoved((ids) => [...ids, line.id]);
                      dirty.current = true;
                    }}
                  >
                    ×
                  </button>
                </div>
                <label className="rr-method-select">
                  How do you get paid?
                  <select
                    aria-label={`Payment type ${line.name || line.id}`}
                    disabled={active}
                    value={line.category || "product_sales"}
                    onChange={(e) => chooseMethod(line, e.target.value)}
                  >
                    {Object.entries(meceMethods).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                {line.advanced ? (
                  <>
                    <h3>{line.name}</h3>
                    <p>
                      Its existing pricing and annual contract terms are
                      preserved.
                    </p>
                    <Link href={assessmentHref("/revenue?advanced=1", id)}>
                      Review detailed contract →
                    </Link>
                  </>
                ) : requiresTerms(line) ? (
                  <details
                    className="rr-payment-details"
                    open={!line.method_form}
                  >
                    <summary>
                      {line.method_form
                        ? `${line.name} · ${full(line.price)} ${String(basis.currency || currency)} ${object(line.method_form).subtype === "fixed" ? "per year" : "per " + line.price_unit} · Edit`
                        : "Add payment details"}
                    </summary>
                    {line.method_form && (
                      <p className="rr-contract-value">
                        {full(line.price)} {String(basis.currency || currency)}{" "}
                        {object(line.method_form).subtype === "fixed"
                          ? "per year"
                          : `per ${line.price_unit}${line.original?.rate_period === "monthly" ? " each month" : ""}`}
                      </p>
                    )}
                    <RevenueMethodForm
                      disabled={active}
                      fixedMethod={line.category}
                      submitLabel="Done"
                      inline
                      key={
                        line.id +
                        line.category +
                        JSON.stringify(line.method_form)
                      }
                      assessmentId={id}
                      revision={Number(state?.revision)}
                      line={
                        {
                          ...line.original,
                          id: line.id,
                          name: line.name,
                          category: line.category,
                          method_form: line.method_form,
                        } as Parameters<typeof RevenueMethodForm>[0]["line"]
                      }
                      onCancel={() => setPanel(null)}
                      onApply={(built) => {
                        patch(line.id, {
                          ...revenueLines({ commercial_lines: [built] })[0],
                          price_period: line.price_period,
                        });
                      }}
                    />
                  </details>
                ) : (
                  <>
                    <div className="rr-line-grid">
                      <label>
                        Name
                        <input
                          aria-label={`Income name ${line.id}`}
                          value={line.name}
                          disabled={active}
                          placeholder={
                            line.kind === "product"
                              ? "e.g. Clean water"
                              : "e.g. Wastewater treatment"
                          }
                          onChange={(e) =>
                            patch(line.id, { name: e.target.value })
                          }
                        />
                      </label>
                      <label>
                        Which stream?
                        <select
                          aria-label={`Quantity source ${line.name || line.id}`}
                          value={line.stream_key || "other"}
                          disabled={active}
                          onChange={(e) => {
                            const key =
                                e.target.value === "other"
                                  ? null
                                  : e.target.value,
                              stream = streams.find((s) => s.key === key),
                              values = array(stream?.values);
                            patch(line.id, {
                              stream_key: key,
                              component: null,
                              price_unit:
                                line.price !== null
                                  ? line.price_unit
                                  : values.some(
                                        (v) => v.property === "volume_flow",
                                      )
                                    ? "m3"
                                    : values.some(
                                          (v) => v.property === "mass_flow",
                                        )
                                      ? "kg"
                                      : line.price_unit,
                            });
                          }}
                        >
                          <option value="other">Enter my own flow rate</option>
                          {streams.map((s) => (
                            <option key={String(s.key)} value={String(s.key)}>
                              {String(s.name || s.identifier)}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Price · {String(basis.currency || currency)}
                        <small className="rr-price-basis">
                          {line.price_period ||
                            String(
                              basis.price_period || new Date().getFullYear(),
                            )}{" "}
                          price basis
                        </small>
                        <div className="rr-price">
                          <input
                            aria-label={`Selling price ${line.name || line.id}`}
                            type="number"
                            min="0"
                            step="any"
                            value={line.price ?? ""}
                            disabled={active}
                            placeholder="Price"
                            onChange={(e) =>
                              patch(line.id, {
                                price: number(e.target.value),
                              })
                            }
                          />
                          <select
                            aria-label={`Price unit ${line.name || line.id}`}
                            value={line.price_unit}
                            disabled={active}
                            onChange={(e) =>
                              patch(line.id, {
                                price_unit: e.target.value,
                              })
                            }
                          >
                            {["kg", "tonne", "m3", "L", "lb"].map((u) => (
                              <option key={u} value={u}>
                                per {u === "m3" ? "m³" : u}
                              </option>
                            ))}
                          </select>
                        </div>
                      </label>
                    </div>
                    {!line.stream_key ? (
                      <div className="rr-custom-rate">
                        <label>
                          Flow rate
                          <input
                            aria-label={`Custom flow rate ${line.name || line.id}`}
                            type="number"
                            min="0"
                            step="any"
                            value={line.rate ?? ""}
                            placeholder="e.g. 2"
                            disabled={active}
                            onChange={(e) =>
                              patch(line.id, {
                                rate: number(e.target.value),
                              })
                            }
                          />
                        </label>
                        <label>
                          Measured in
                          <select
                            aria-label={`Rate unit ${line.name || line.id}`}
                            value={line.rate_unit}
                            disabled={active}
                            onChange={(e) =>
                              patch(line.id, {
                                rate_unit: e.target.value,
                              })
                            }
                          >
                            {rateUnits.map((u) => (
                              <option key={u} value={u}>
                                {u
                                  .replace("m3", "m³")
                                  .replace("/h", " / hour")
                                  .replace("/day", " / day")
                                  .replace("/min", " / minute")
                                  .replace("/s", " / second")}
                              </option>
                            ))}
                          </select>
                        </label>
                        <p>Use an amount per hour, day or minute.</p>
                      </div>
                    ) : (
                      <p className="rr-source">
                        {observed
                          ? `Flow from your file: ${full(observed.normalized_value)} ${String(observed.normalized_unit).replace("/h", " per hour").replace("/day", " per day")}`
                          : "Choose a matching flow and price unit."}
                      </p>
                    )}
                    <div className="rr-equation">
                      <span>Flow rate</span>
                      <b>×</b>
                      <span>Price / {line.price_unit}</span>
                      <b>×</b>
                      <span>Operating time</span>
                      <b>=</b>
                      <strong>
                        {amount(income(line))} {currency}
                        <small>Last calculated yearly income</small>
                      </strong>
                    </div>
                  </>
                )}
                <details className="rr-more-options">
                  <summary>More options</summary>
                  <p className="rr-method-formula">
                    {meceFormula[line.category || "product_sales"]}
                  </p>
                  {line.kind === "product" && (
                    <label className="rr-method-select">
                      Product type
                      <select
                        aria-label={`Product role ${line.name || line.id}`}
                        value={line.role || "main_product"}
                        disabled={active}
                        onChange={(e) =>
                          patch(line.id, {
                            role: e.target.value as
                              | "main_product"
                              | "byproduct",
                          })
                        }
                      >
                        <option value="main_product">Main product</option>
                        <option value="byproduct">
                          Other product / by-product
                        </option>
                      </select>
                    </label>
                  )}
                  {observed && (
                    <p className="rr-source">
                      Found in {String(observed.sheet || "workbook")} · cell{" "}
                      {String(observed.cell || "")}
                    </p>
                  )}
                  <button
                    className="secondary"
                    onClick={() => setPanel(line.id)}
                  >
                    Sales settings & price year
                  </button>
                </details>
                <PriceReview
                  line={line}
                  busy={active}
                  proposal={
                    object(
                      array(state?.research_drafts)
                        .filter((d) => d.target_id === line.id)
                        .at(-1),
                    ).price_review as Row | undefined
                  }
                  researchNotice={String(
                    object(
                      array(state?.research_drafts)
                        .filter((d) => d.target_id === line.id)
                        .at(-1),
                    ).price_review_notice ||
                      (object(state?.research_job).target_id === line.id &&
                      object(state?.research_job).status === "failed"
                        ? object(state?.research_job).notice ||
                          "Research failed; previous inputs retained."
                        : ""),
                  )}
                  onChange={(change) => patch(line.id, change)}
                  onResearch={() => void researchPrice(line)}
                  onAccept={() =>
                    void acceptPrice(
                      line,
                      object(
                        object(
                          array(state?.research_drafts)
                            .filter((d) => d.target_id === line.id)
                            .at(-1),
                        ).price_review,
                      ),
                    )
                  }
                />
              </article>
            );
          })}
        </div>
        {pending.length > 0 && (
          <details>
            <summary>
              {pending.length} interpreted income methods need details
            </summary>
            {pending.map((p) => (
              <div className="rr-pending" key={String(p.id)}>
                <strong>{String(p.name || p.id)}</strong>
                <p>
                  {String(
                    p.description ||
                      p.context_quote ||
                      "Supply the stream or a custom rate and its price.",
                  )}
                </p>
                <button
                  disabled={active || lines.some((r) => r.id === p.id)}
                  onClick={() =>
                    add(
                      p.category === "product_sales" ? "product" : "service",
                      p,
                    )
                  }
                >
                  Complete income method
                </button>
              </div>
            ))}
          </details>
        )}
        <div className="rr-save">
          <span>
            {ready} income {ready === 1 ? "source" : "sources"} ready
          </span>
          <button
            className="secondary"
            disabled={active || !isDirty}
            onClick={() => void save(false)}
          >
            Save
          </button>
          <button
            disabled={active || !lines.length}
            onClick={() => void save(true)}
          >
            {active ? "Working…" : "Calculate income →"}
          </button>
        </div>
        <small className="rr-consent">
          Calculate uses the details shown here. You can change them any time.
        </small>
      </section>
    </>
  );
  return (
    <div className={`shell ${dark ? "dark" : ""}`} data-page="revenue">
      <a className="skip-link" href="#revenue-workspace">
        Skip to revenue
      </a>
      <aside>
        <Link className="brand" href={assessmentHref("/entry", id)}>
          ≋ flowvalue <small>AI</small>
        </Link>
        <p className="eyebrow">WORKSPACE</p>
        <div className="project">
          {String(state?.filename || "Revenue study")}
          <small>Rates, prices and operating time</small>
        </div>
        <WorkspaceNavigation page="revenue" id={id} />
      </aside>
      <main>
        <header>
          <span className="breadcrumb">
            Workspace › <strong>Revenue</strong>
          </span>
          <div className="header-actions">
            <span className="connection-state">
              <i />
              {active ? "Updating revenue" : "Analyst workspace"}
            </span>
            <button
              className="theme-toggle"
              aria-label="Toggle dark mode"
              onClick={() => {
                setDark(!dark);
                localStorage.setItem(
                  "flowvalue-theme",
                  !dark ? "dark" : "light",
                );
              }}
            >
              {dark ? "☀" : "☾"}
            </button>
          </div>
        </header>
        <div className="content revenue-rate-workspace" id="revenue-workspace">
          <StageJourney page="revenue" id={id} />
          <div className="rr-heading">
            <h1>Revenue</h1>
            <button
              disabled={active || !id}
              onClick={() => setPanel("assistant")}
            >
              ✦ Revenue assistant
            </button>
          </div>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          {notice && (
            <p className="notice" role="status">
              {notice}
            </p>
          )}
          {!id ? (
            <section>
              <h2>Start with your process</h2>
              <p>
                Select an assessment to connect income to its material streams.
              </p>
              <Link href="/entry">Open Entry →</Link>
            </section>
          ) : (
            <>
              <div className="rr-summary">
                <article>
                  <small>
                    Annual income · operating year {String(latest?.year || "—")}
                  </small>
                  <strong>
                    {amount(latest?.sales_revenue)} <em>{currency}</em>
                  </strong>
                  <span>
                    {isDirty
                      ? "Unsaved changes · saved results shown"
                      : revenueStage.result_is_stale
                        ? "Recalculation required"
                        : "Saved Python calculation"}
                  </span>
                </article>
                <article>
                  <small>Total income · analysis period</small>
                  <strong>
                    {amount(total)} <em>{currency}</em>
                  </strong>
                  <span>{life} operating years · undiscounted</span>
                </article>
                <button onClick={() => setPanel("calendar")}>
                  <small>Operating calendar ↗</small>
                  <strong>
                    {days} <em>days / year</em>
                  </strong>
                  <span>
                    {hours} h / day · annual production ramp applied once
                  </span>
                </button>
              </div>
              {panel !== "assistant" && incomeEditor}
              <section className="rr-forecast">
                <div className="rr-section-head">
                  <div>
                    <h2>Income over time</h2>
                    <p>
                      {construction} construction years · {life} operating
                      years. Income follows the saved production and sales
                      schedule.
                    </p>
                  </div>
                  <Link href={assessmentHref("/cashflow", id)}>
                    Edit annual ramp ↗
                  </Link>
                </div>
                {annual.length ? (
                  <svg
                    viewBox="0 0 900 230"
                    role="img"
                    aria-label="Annual revenue forecast from the saved Python calculation"
                  >
                    {[0, 0.5, 1].map((v) => (
                      <g key={v}>
                        <line
                          x1="60"
                          x2="880"
                          y1={185 - v * 150}
                          y2={185 - v * 150}
                          stroke="currentColor"
                          opacity=".12"
                        />
                        <text x="2" y={189 - v * 150}>
                          {amount(maxAnnual * v)}
                        </text>
                      </g>
                    ))}
                    {annual.map((r, i) => (
                      <g key={String(r.year)}>
                        <rect
                          x={65 + (i * 800) / annual.length}
                          y={
                            185 -
                            (Number(r.sales_revenue || 0) / maxAnnual) * 150
                          }
                          width={Math.max(2, 800 / annual.length - 6)}
                          height={
                            (Number(r.sales_revenue || 0) / maxAnnual) * 150
                          }
                          rx="3"
                        >
                          <title>{`Project year ${Number(r.year) + construction}: ${full(r.sales_revenue)} ${currency}`}</title>
                        </rect>
                        {(i === 0 ||
                          i === annual.length - 1 ||
                          i % Math.ceil(annual.length / 8) === 0) && (
                          <text
                            x={65 + ((i + 0.5) * 800) / annual.length}
                            y="210"
                            textAnchor="middle"
                          >
                            Y{Number(r.year) + construction}
                          </text>
                        )}
                      </g>
                    ))}
                  </svg>
                ) : (
                  <div className="rr-empty">
                    Your forecast appears after calculating the income sources
                    above.
                  </div>
                )}
              </section>
              <div className="rr-links">
                <Link href={assessmentHref("/revenue?advanced=1", id)}>
                  Advanced contracts, credits & detailed ledger ↗
                </Link>
                <Link href={assessmentHref("/financial-modelling", id)}>
                  Open financial model →
                </Link>
              </div>
            </>
          )}
          {panel && (
            <div
              className="rr-backdrop"
              onMouseDown={(e) => {
                if (e.target === e.currentTarget) setPanel(null);
              }}
            >
              <div
                ref={dialog}
                className={`rr-drawer ${panel === "assistant" ? "rr-mece-dialog" : ""}`}
                role="dialog"
                aria-modal="true"
                aria-label="Revenue workspace details"
              >
                <div className="rr-drawer-head">
                  <div>
                    <small>
                      REVENUE /{" "}
                      {panel === "assistant"
                        ? "ASSISTANT"
                        : panel === "calendar"
                          ? "CALENDAR"
                          : "ASSUMPTIONS"}
                    </small>
                    <h2>
                      {panel === "assistant"
                        ? "Your income"
                        : panel === "calendar"
                          ? "Operating time"
                          : selected?.name || "Income assumptions"}
                    </h2>
                  </div>
                  <button
                    ref={close}
                    aria-label="Close revenue details"
                    onClick={() => setPanel(null)}
                  >
                    ✕
                  </button>
                </div>
                <div className="rr-drawer-body">
                  {panel === "assistant" ? (
                    <>
                      {incomeEditor}
                      <details className="rr-reinterpret" open={!lines.length}>
                        <summary>Describe your income</summary>
                        <p>
                          Describe each income source and any prices you know.
                          The assistant maps it to your streams; Python
                          calculates the money.
                        </p>
                        <label>
                          Revenue description
                          <textarea
                            aria-label="Revenue description"
                            value={text}
                            disabled={active}
                            onChange={(e) => setText(e.target.value)}
                            placeholder="We sell the clean-water outlet for USD 2/m3 and charge USD 1/m3 of wastewater treated."
                          />
                        </label>
                        <div className="rr-assistant-hint">
                          <strong>
                            Stream or rate. Price. Operating time.
                          </strong>
                          <p>
                            Example for a custom source: “We sell 2 m3/hour at
                            USD 5/m3.” No one-off quantity is needed.
                          </p>
                        </div>
                        <button
                          disabled={active || !text.trim()}
                          onClick={() => void interpret()}
                        >
                          {active
                            ? "Preparing income lines…"
                            : "Draft income lines with AI →"}
                        </button>
                        <small>
                          AI usage charges apply. No external price research
                          starts automatically. Review the draft before
                          calculating.
                        </small>
                      </details>
                      {typeof object(state?.ai).revenue_refresh_error ===
                        "string" && (
                        <p className="error">
                          {String(object(state?.ai).revenue_refresh_error)}
                        </p>
                      )}
                    </>
                  ) : panel === "calendar" ? (
                    <>
                      <p>
                        Flow rates are annualized using operating hours, then
                        adjusted by the saved annual ramp. The analysis horizon
                        comes from the project calendar.
                      </p>
                      <label>
                        Operating days / year
                        <input
                          aria-label="Revenue operating days"
                          type="number"
                          min="1"
                          max="366"
                          value={days}
                          onChange={(e) => {
                            setDays(Number(e.target.value));
                            setTimeDirty(true);
                            dirty.current = true;
                          }}
                        />
                      </label>
                      <label>
                        Operating hours / day
                        <input
                          aria-label="Revenue operating hours"
                          type="number"
                          min="0"
                          max="24"
                          step="any"
                          value={hours}
                          onChange={(e) => {
                            setHours(Number(e.target.value));
                            setTimeDirty(true);
                            dirty.current = true;
                          }}
                        />
                      </label>
                      <p>
                        {life} operating years, following {construction}{" "}
                        construction years. Calendar changes affect shared
                        operating costs too.
                      </p>
                      <Link href={assessmentHref("/cashflow", id)}>
                        Change analysis horizon and annual ramp →
                      </Link>
                      <button
                        disabled={active}
                        onClick={() => void save(false)}
                      >
                        Save calendar
                      </button>
                    </>
                  ) : (
                    selected && (
                      <>
                        <p>
                          These are explicit user planning assumptions. They do
                          not establish product quality or a sales contract.
                        </p>
                        {selected.kind === "product" &&
                          (
                            [
                              "allocation_fraction",
                              "saleable_fraction",
                              "sold_fraction",
                            ] as const
                          ).map((key) => (
                            <label key={key}>
                              {
                                {
                                  allocation_fraction:
                                    "Share of stream allocated",
                                  saleable_fraction:
                                    "Share meeting saleable quality",
                                  sold_fraction:
                                    "Share of saleable output sold",
                                }[key]
                              }{" "}
                              · %
                              <input
                                type="number"
                                min="0"
                                max="100"
                                step="any"
                                value={selected[key] * 100}
                                onChange={(e) =>
                                  patch(selected.id, {
                                    [key]: Number(e.target.value) / 100,
                                  })
                                }
                              />
                            </label>
                          ))}
                        {selected.stream_key && (
                          <label>
                            Component basis
                            <select
                              value={selected.component || ""}
                              onChange={(e) =>
                                patch(selected.id, {
                                  component: e.target.value || null,
                                })
                              }
                            >
                              <option value="">Whole stream</option>
                              {Array.from(
                                new Set(
                                  array(
                                    streams.find(
                                      (s) => s.key === selected.stream_key,
                                    )?.values,
                                  )
                                    .filter((v) => v.component)
                                    .map((v) => String(v.component)),
                                ),
                              ).map((c) => (
                                <option key={c}>{c}</option>
                              ))}
                            </select>
                          </label>
                        )}
                        <label>
                          Price basis year / period
                          <input
                            value={
                              selected.price_period ||
                              String(basis.price_period || "")
                            }
                            onChange={(e) =>
                              patch(selected.id, {
                                price_period: e.target.value,
                              })
                            }
                          />
                        </label>
                        <label>
                          Basis / notes
                          <textarea
                            value={selected.rationale}
                            onChange={(e) =>
                              patch(selected.id, { rationale: e.target.value })
                            }
                          />
                        </label>
                        <p>
                          Editing a processing fee applies that rate across the
                          modelled operating years. For year-specific prices,
                          minimum payments or commercial terms, use Advanced
                          contracts.
                        </p>
                        <button
                          disabled={active}
                          onClick={() => void save(false)}
                        >
                          Save assumptions
                        </button>
                      </>
                    )
                  )}
                  {error && (
                    <p className="error" role="alert">
                      {error}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
