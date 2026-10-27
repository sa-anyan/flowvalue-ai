"use client";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/client-api";
import {
  apiError,
  defaultIncentive,
  usd,
  type AssessmentRequest,
  type EquipmentSpec,
  type Incentive,
} from "@/lib/assessment";
import { importScopeNotes, type NativeImport } from "@/lib/workspace";
type Tornado = {
  baseline_npv_usd: number;
  swing_fraction: number;
  rows: {
    label: string;
    low_input_npv_usd: number;
    high_input_npv_usd: number;
    low_delta_usd: number;
    high_delta_usd: number;
    span_usd: number;
  }[];
};
export function EngineeringTools({
  project,
  scenario,
  ready,
  onProject,
  native,
  aiAvailable,
}: {
  aiAvailable: boolean;
  project: AssessmentRequest;
  scenario: AssessmentRequest;
  ready: boolean;
  onProject: (p: AssessmentRequest) => void;
  native: NativeImport | null;
}) {
  const [message, setMessage] = useState(""),
    [draft, setDraft] = useState<{
      native: NativeImport | null;
      text: string;
    } | null>(null),
    [busy, setBusy] = useState("");
  const [indices, setIndices] = useState<
    {
      period: string;
      value: number;
      source_title: string;
      source_url: string;
      status: string;
      retrieved_on: string;
    }[]
  >([]);
  const [catalog, setCatalog] = useState<
    {
      category: string;
      type: string;
      units: string;
      s_lower: number;
      s_upper: number;
    }[]
  >([]);
  const [correlation, setCorrelation] = useState(0),
    [parameter, setParameter] = useState(500),
    [unitName, setUnitName] = useState("LIB-101");
  const [sensitivity, setSensitivity] = useState<{
      signature: string;
      data: Tornado;
    } | null>(null),
    [memo, setMemo] = useState<{
      signature: string;
      text: string;
      model: string;
      generated_at: string;
    } | null>(null);
  const mappingText =
    draft?.native === native
      ? draft.text
      : JSON.stringify(native?.equipment || [], null, 2);
  const signature = JSON.stringify(scenario),
    policy = project.financial.incentive || defaultIncentive;
  useEffect(() => {
    apiFetch("/api/indices/cepci")
      .then((r) => r.json())
      .then((r) => setIndices(r.records || []))
      .catch(() => {});
    apiFetch("/api/integrations/catalog")
      .then((r) => r.json())
      .then((r) => setCatalog(r.correlations || []))
      .catch(() => {});
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    if (!ready) return;
    const t = setTimeout(() => {
      apiFetch("/api/assessment/tornado", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: signature,
        signal: controller.signal,
      })
        .then(async (r) => {
          if (!r.ok) throw Error(await apiError(r));
          setSensitivity({ signature, data: await r.json() });
        })
        .catch((e) => {
          if (e.name !== "AbortError") setMessage(e.message);
        });
    }, 350);
    return () => {
      clearTimeout(t);
      controller.abort();
    };
  }, [ready, signature]);
  function policyChange(change: Partial<Incentive>) {
    onProject({
      ...project,
      financial: { ...project.financial, incentive: { ...policy, ...change } },
    });
  }
  async function addLibrary() {
    setBusy("library");
    try {
      const selected = catalog[correlation];
      const r = await apiFetch("/api/integrations/openpytea/equipment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: unitName,
          parameter,
          category: selected.category,
          equipment_type: selected.type,
          material: "Carbon steel",
          target_year: 2024,
        }),
      });
      if (!r.ok) throw Error(await apiError(r));
      const x = await r.json();
      if (
        project.costing.equipment.some((e) => e.unit_id === x.equipment.unit_id)
      )
        throw Error("Use a unique unit ID");
      onProject({
        ...project,
        costing: {
          ...project.costing,
          equipment: [...project.costing.equipment, x.equipment],
        },
      });
      setMessage(x.warning);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Library request failed");
    } finally {
      setBusy("");
    }
  }
  async function applyMapping() {
    setBusy("mapping");
    try {
      const equipment = JSON.parse(mappingText) as EquipmentSpec[];
      if (!Array.isArray(equipment) || !equipment.length)
        throw Error("Supply a nonempty equipment JSON array");
      const r = await apiFetch("/api/costing/bom", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...project.costing, equipment }),
      });
      if (!r.ok) throw Error(await apiError(r));
      onProject({
        ...project,
        engineering_notes: native
          ? importScopeNotes(native, equipment)
          : project.engineering_notes,
        costing: { ...project.costing, equipment },
      });
      setMessage(
        "Mapped BOM replaced. Review retained financial assumptions and excluded units.",
      );
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Invalid mapping");
    } finally {
      setBusy("");
    }
  }
  async function generateMemo() {
    if (!ready || !aiAvailable) return;
    setBusy("memo");
    try {
      const r = await apiFetch("/api/copilot/executive-memo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: signature,
      });
      if (!r.ok) throw Error(await apiError(r));
      const data = await r.json();
      setMemo({
        signature,
        text: data.markdown,
        model: data.model,
        generated_at: data.generated_at,
      });
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Memo failed");
    } finally {
      setBusy("");
    }
  }
  function downloadMemo() {
    if (!memo) return;
    const a = document.createElement("a"),
      url = URL.createObjectURL(
        new Blob(
          [
            `> AI draft · ${memo.generated_at} · ${memo.model}\n> Computed scenario only; no live market research. Review before distribution.\n\n${memo.text}`,
          ],
          { type: "text/markdown" },
        ),
      );
    a.href = url;
    a.download = "flowvalue-executive-memo.md";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <div className="engineering-tools">
      {native && (
        <details className="panel extension-panel" open>
          <summary>DWSIM import review</summary>
          <p>
            {native.source}. {native.streams.length} streams ·{" "}
            {native.units.length} operations · {native.equipment.length} mapped
            estimates.
          </p>
          {native.warnings.map((w, i) => (
            <p key={i} className="engineering-warning">
              {w}
            </p>
          ))}
          <div className="native-unit-list">
            {native.units.map((u) => (
              <div key={u.native_id}>
                <strong>
                  {u.unit_id} · {u.native_type}
                </strong>
                <span>
                  {project.costing.equipment.some(
                    (e) => e.unit_id === u.unit_id,
                  )
                    ? "Mapped in active BOM"
                    : "Excluded from active BOM · needs engineering input"}
                </span>
                {u.missing_inputs.map((x, i) => (
                  <p key={i}>Missing in original simulation: {x}</p>
                ))}
                {u.warnings.map((x, i) => (
                  <p key={i}>Missing in original simulation: {x}</p>
                ))}
              </div>
            ))}
          </div>
          <p>
            Incomplete operations are excluded from the priced BOM. No
            feedstock, product price or annual operating budget is inferred. A
            retained demo financial basis remains a demo.
          </p>
          <details>
            <summary>Review or complete equipment mapping</summary>
            <textarea
              aria-label="DWSIM equipment mapping JSON"
              value={mappingText}
              onChange={(e) => setDraft({ native, text: e.target.value })}
              rows={12}
            />
            <Button disabled={!!busy} onClick={applyMapping}>
              Validate & replace BOM
            </Button>
          </details>
          <p>
            Collapse this review with its heading. Native topology and review
            notes remain part of the project.
          </p>
        </details>
      )}
      <section className="panel extension-panel">
        <div className="panel-heading">
          <div>
            <h2>Engineering integrations</h2>
            <p>OpenPyTEA correlations and trusted BioSTEAM snapshots</p>
          </div>
          <a className="flow-link" href="/process-flow">
            Open interactive process flow ↗
          </a>
        </div>
        <details>
          <summary>Add an OpenPyTEA equipment estimate</summary>
          <p>
            Uses the installed OpenPyTEA library (2024 index basis). Its direct
            installed cost can differ from Turton bare-module scope.
            Carbon-steel basis; verify applicability and ranges.
          </p>
          <div className="extension-actions">
            <label>
              Unit ID
              <input
                value={unitName}
                onChange={(e) => setUnitName(e.target.value)}
              />
            </label>
            <label>
              Correlation
              <select
                value={correlation}
                onChange={(e) => setCorrelation(Number(e.target.value))}
              >
                {catalog.map((c, i) => (
                  <option key={i} value={i}>
                    {c.category} / {c.type}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Characteristic size · {catalog[correlation]?.units}
              <input
                type="number"
                value={parameter}
                onChange={(e) => setParameter(Number(e.target.value))}
              />
            </label>
            <Button
              disabled={!!busy || !ready || !catalog.length}
              onClick={addLibrary}
            >
              Add library estimate
            </Button>
          </div>
          <p>
            Database range: {catalog[correlation]?.s_lower}–
            {catalog[correlation]?.s_upper} {catalog[correlation]?.units}.
            Library extrapolation warnings are retained.
          </p>
        </details>
        <details>
          <summary>CEPCI source catalog</summary>
          <p>
            Licensed observations are added by an operator with source, date and
            reviewer. No live subscription feed is connected. Your currently
            selected index: {project.costing.settings.cepci_current}.
          </p>
          {indices.map((x, i) => (
            <div className="index-record" key={i}>
              <a href={x.source_url} target="_blank" rel="noreferrer">
                {x.period} · {x.value} · {x.status} · {x.source_title}
              </a>
              <small>Retrieved {x.retrieved_on}</small>
              <Button
                variant="outline"
                onClick={() =>
                  onProject({
                    ...project,
                    costing: {
                      ...project.costing,
                      settings: {
                        ...project.costing.settings,
                        cepci_current: x.value,
                      },
                    },
                  })
                }
              >
                Use {x.value}
              </Button>
            </div>
          ))}
        </details>
      </section>
      <section className="panel extension-panel">
        <h2>Production credits & subsidies</h2>
        <p>
          User-defined cash-flow scenario. A 45V label does not establish
          eligibility. Confirm jurisdiction, emissions tier, start dates, wage
          rules and monetization. Credit units must match the model’s product
          units (45V uses kg hydrogen).
        </p>
        <div className="extension-actions">
          <label>
            Policy label
            <input
              aria-label="Incentive label"
              value={policy.name}
              onChange={(e) => policyChange({ name: e.target.value })}
            />
          </label>
          <label>
            USD / product unit
            <input
              aria-label="Production credit rate"
              type="number"
              min={0}
              value={policy.rate_usd_per_unit}
              onChange={(e) =>
                policyChange({ rate_usd_per_unit: Number(e.target.value) })
              }
            />
          </label>
          <label>
            Eligible fraction
            <input
              aria-label="Eligible production fraction"
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={policy.eligible_fraction}
              onChange={(e) =>
                policyChange({ eligible_fraction: Number(e.target.value) })
              }
            />
          </label>
          <label>
            First operating year
            <input
              type="number"
              min={1}
              max={100}
              value={policy.start_year}
              onChange={(e) =>
                policyChange({ start_year: Number(e.target.value) })
              }
            />
          </label>
          <label>
            Duration (years)
            <input
              aria-label="Credit duration"
              type="number"
              min={1}
              max={100}
              value={policy.duration_years}
              onChange={(e) =>
                policyChange({ duration_years: Number(e.target.value) })
              }
            />
          </label>
          <label>
            Monetization
            <select
              value={policy.treatment}
              onChange={(e) =>
                policyChange({
                  treatment: e.target.value as Incentive["treatment"],
                })
              }
            >
              <option value="cash_payment">
                Cash payment outside taxable income (assumed)
              </option>
              <option value="tax_offset">
                Tax offset, capped at annual tax (no carryforward)
              </option>
            </select>
          </label>
        </div>
        <label className="extension-full-label">
          Eligibility and treatment basis
          <textarea
            aria-label="Incentive eligibility basis"
            value={policy.basis}
            onChange={(e) => policyChange({ basis: e.target.value })}
          />
        </label>
        <label className="extension-checkbox">
          <input
            type="checkbox"
            checked={policy.eligibility_confirmed}
            onChange={(e) =>
              policyChange({
                eligibility_confirmed: e.target.checked,
                enabled: e.target.checked ? policy.enabled : false,
              })
            }
          />
          I have checked the eligibility and monetization assumptions.
        </label>
        <label className="extension-checkbox">
          <input
            aria-label="Enable production credit"
            type="checkbox"
            disabled={!policy.eligibility_confirmed || !policy.basis.trim()}
            checked={policy.enabled}
            onChange={(e) => policyChange({ enabled: e.target.checked })}
          />
          Include this credit in cash flows and exports
        </label>
        <a
          href="https://www.irs.gov/credits-deductions/clean-hydrogen-production-credit"
          target="_blank"
          rel="noreferrer"
        >
          IRS 45V source ↗
        </a>
        <p>
          LCOP remains pre-tax and before credits; NPV, IRR and uncertainty
          include the selected credit.
        </p>
      </section>
      <section className="panel extension-panel">
        <h2>Tornado sensitivity · ±20%</h2>
        <p>
          One parameter changes at a time. Bars show NPV change from{" "}
          {sensitivity
            ? usd(sensitivity.data.baseline_npv_usd)
            : "the current baseline"}
          . Category quantities remain fixed.
        </p>
        {sensitivity && (
          <>
            <p>
              {sensitivity.signature === signature && ready
                ? "Current scenario"
                : "Updating · previous scenario shown"}
            </p>
            {sensitivity.data.rows.map((row) => {
              const max = Math.max(
                ...sensitivity.data.rows.map((r) =>
                  Math.max(
                    Math.abs(r.low_delta_usd),
                    Math.abs(r.high_delta_usd),
                  ),
                ),
                1,
              );
              return (
                <div className="tornado-row" key={row.label}>
                  <strong>{row.label}</strong>
                  <div className="tornado-track">
                    <span
                      className="tornado-negative"
                      style={{
                        left: `${50 + (row.low_delta_usd / max) * 50}%`,
                        width: `${(Math.abs(Math.min(0, row.low_delta_usd)) / max) * 50}%`,
                      }}
                    />
                    <span
                      className="tornado-positive"
                      style={{
                        left: "50%",
                        width: `${(Math.max(0, row.high_delta_usd) / max) * 50}%`,
                      }}
                    />
                  </div>
                  <small>
                    −20%: {usd(row.low_input_npv_usd, true)} · +20%:{" "}
                    {usd(row.high_input_npv_usd, true)}
                  </small>
                </div>
              );
            })}
          </>
        )}
      </section>
      <section className="panel extension-panel">
        <div className="panel-heading">
          <div>
            <h2>Executive investment memo</h2>
            <p>
              AI draft grounded in this scenario’s computed economics and
              sensitivities.
            </p>
          </div>
          <Button
            disabled={!!busy || !ready || !aiAvailable}
            onClick={generateMemo}
          >
            {busy === "memo" ? "Drafting…" : "Draft executive memo"}
          </Button>
        </div>
        {!aiAvailable && (
          <p>
            Memo generation is unavailable until the AI connection is
            configured. Financial exports remain available.
          </p>
        )}
        {memo && (
          <>
            <small>
              Generated {new Date(memo.generated_at).toLocaleString()} ·{" "}
              {memo.model} · Computed scenario only; no live research.
            </small>
            <p>
              {memo.signature === signature
                ? "Draft · review before distribution"
                : "Stale draft · scenario changed; regenerate before use"}
            </p>
            <div className="memo-content">
              <ReactMarkdown skipHtml>{memo.text}</ReactMarkdown>
            </div>
            <Button
              variant="outline"
              disabled={memo.signature !== signature}
              onClick={downloadMemo}
            >
              Download memo (.md)
            </Button>
          </>
        )}
      </section>
      {message && (
        <p role="status" className="engineering-message">
          {message}
        </p>
      )}
    </div>
  );
}
