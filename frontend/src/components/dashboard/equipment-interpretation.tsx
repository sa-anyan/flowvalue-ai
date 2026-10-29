"use client";

import { useEffect, useRef, useState } from "react";
import type { BalanceReport } from "@/lib/balance";
import { apiFetch } from "@/lib/client-api";
import { apiError } from "@/lib/assessment";

import { isInterpretationDraft, interpretationRecords, interpretationContextVersion, interpretationStorageKey, type Saved } from "@/lib/equipment-interpretation";
const storageKey = interpretationStorageKey;
export type InterpretationRecords = { report: BalanceReport | null; description: string; records: Saved[] };

export function EquipmentInterpretation({ report, processDescription, onRecords }: { report: BalanceReport | null; processDescription: string; onRecords: (value: InterpretationRecords) => void }) {
  const units = report?.entities.filter(item => item.kind === "equipment") ?? [];
  const [selected, setSelected] = useState("");
  const selectedKey = units.some(item => item.key === selected) ? selected : units[0]?.key ?? "";
  const [state, setState] = useState<Saved | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [status, setStatus] = useState<{ can_generate: boolean; message: string; model: string } | null>(null);
  const body = JSON.stringify({ report, equipment_key: selectedKey, process_description: processDescription.slice(0, 2000) });
  const contextBody = JSON.stringify({ report, process_description: processDescription.slice(0, 2000) });
  const [records, setRecords] = useState<Saved[]>([]);
  const currentInput = useRef(body);
  useEffect(() => { currentInput.current = body; }, [body]);
  const [fingerprint, setFingerprint] = useState<{ body: string; hash: string } | null>(null);
  const stamp = fingerprint?.body === contextBody ? `${fingerprint.hash}:${selectedKey}` : "";
  useEffect(() => {
    let alive = true;
    crypto.subtle.digest("SHA-256", new TextEncoder().encode(interpretationContextVersion + contextBody)).then(buffer => {
      if (!alive) return;
      const hash = Array.from(new Uint8Array(buffer)).map(n => n.toString(16).padStart(2, "0")).join("");
      setFingerprint({ body: contextBody, hash });
      try {
        const saved = interpretationRecords(JSON.parse(sessionStorage.getItem(storageKey) ?? "null"));
        setRecords(saved.filter(record => record.stamp.startsWith(`${hash}:`)));
      } catch { /* Corrupt local drafts are ignored; parsed data is unchanged. */ }
    }).catch(() => { if (alive) setError("Could not fingerprint this input. AI interpretation is unavailable."); });
    return () => { alive = false; };
  }, [contextBody]);
  useEffect(() => {
    let alive = true;
    apiFetch("/api/copilot/status").then(async response => {
      if (!response.ok) throw new Error(await apiError(response));
      const value = await response.json();
      if (alive) setStatus(value);
    }).catch((e: Error) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, []);
  const current = records.find(record => record.stamp === stamp && record.data.equipment_key === selectedKey) ?? null;
  useEffect(() => {
    onRecords({ report, description: processDescription, records: stamp ? records.filter(record => record.stamp.startsWith(`${fingerprint?.hash}:`)) : [] });
  }, [records, stamp, fingerprint?.hash, report, processDescription, onRecords]);
  const persist = (saved: Saved) => {
    setState(saved);
    const updated = [...records.filter(record => record.stamp !== saved.stamp), saved].slice(-20);
    setRecords(updated);
    try { sessionStorage.setItem(storageKey, JSON.stringify(updated)); }
    catch { setError("Draft is visible but could not be saved in this browser tab. Download it before leaving."); }
  };
  async function interpret() {
    if (!report || !selectedKey || !stamp) return;
    const snapshot = body, fingerprint = stamp;
    setBusy(true); setError("");
    try {
      const response = await apiFetch("/api/equipment/interpret", { method: "POST", headers: { "Content-Type": "application/json" }, body: snapshot });
      if (!response.ok) throw new Error(await apiError(response));
      const data: unknown = await response.json();
      if (!isInterpretationDraft(data)) throw new Error("Invalid interpretation response. No draft accepted.");
      if (currentInput.current !== snapshot) { setError("Input changed during interpretation. The previous result was discarded."); return; }
      persist({ stamp: fingerprint, data, review: "" });
    } catch (e) { setError(e instanceof Error ? e.message : "AI interpretation failed."); }
    finally { setBusy(false); }
  }
  function download() {
    if (!current) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(current, null, 2)], { type: "application/json" }));
    const link = document.createElement("a"); link.href = url; link.download = "equipment-interpretation-draft.json"; link.click(); URL.revokeObjectURL(url);
  }
  return <section className="panel equipment-catalog equipment-interpretation" aria-label="AI engineering interpretation">
    <h2>AI engineering interpretation</h2>
    <p className="muted">Propose a catalog basis and investigate modifications before costing. Hypotheses require engineering review.</p>
    {!units.length ? <p>Upload a workbook with detected equipment to begin.</p> : <>
      <label htmlFor="interpret-unit">Equipment</label>
      <select id="interpret-unit" value={selectedKey} disabled={busy} onChange={e => setSelected(e.target.value)}>
        {units.map(unit => <option key={unit.key} value={unit.key}>{unit.identifier} · {unit.id_evidence.sheet}{unit.case ? ` · ${unit.case}` : ""}</option>)}
      </select>
      <p className="muted">Sends selected equipment and stream properties/composition, bounded same-sheet/case process context, and up to 2,000 characters of your Entry description to OpenAI. One request per click; usage charges apply. No raw files, web research or automatic cost changes.</p>
      <button type="button" className="entry-analysis-link" onClick={interpret} disabled={busy || !status?.can_generate || !stamp}>{busy ? "Interpreting…" : "Interpret selected equipment"}</button>
      <p className="muted">{status ? `${status.model} · ${status.message}` : "Checking AI connection settings…"}</p>
    </>}
    {error && <p className="error-banner" role="alert">{error}</p>}
    {state && !current && <p role="status">Previous interpretation is stale for these inputs. Run a new interpretation.</p>}
    {current && <article>
      <h3>{current.data.draft.interpreted_identity}</h3>
      <p className="muted">AI draft · {current.data.model} · {current.data.generated_at}</p>
      <h4>Workbook observations</h4><ul>{current.data.draft.observations.map((observation, i) => {
        const source = current.data.observation_sources.find(item => item.id === observation.evidence_id);
        return <li key={i}>“{observation.quote}” <small>{source?.sheet}!{source?.cell}</small></li>;
      })}</ul>
      <h4>Provisional catalog methods</h4>
      {!current.data.draft.candidates.length && <p>No supported candidate proposed.</p>}
      {current.data.draft.candidates.map(candidate => {
        const source = current.data.candidate_sources.find(item => item.id === candidate.catalog_id);
        return <div key={candidate.catalog_id}><strong>{source?.name}</strong><p>{candidate.rationale}</p>
          {source?.source_refs.map(ref => <small className="block" key={ref.source_id}>{ref.label ?? ref.source_id} · p. {ref.printed_page} / PDF p. {ref.pdf_page}</small>)}
          <h4>Differences / modifications to investigate</h4><ul>{candidate.differences.map(text => <li key={text}>{text}</li>)}</ul>
          <h4>Missing inputs</h4><ul>{candidate.missing_inputs.map(text => <li key={text}>{text}</li>)}</ul>
        </div>;
      })}
      <h4>Engineering hypotheses — unverified</h4><ul>{current.data.draft.engineering_hypotheses.map(text => <li key={text}>{text}</li>)}</ul>
      <h4>Clarifications</h4><ul>{current.data.draft.clarification_questions.map(text => <li key={text}>{text}</li>)}</ul>
      <h4>Uncertainty drivers — no numerical range established</h4><ul>{current.data.draft.uncertainty_drivers.map(text => <li key={text}>{text}</li>)}</ul>
      <h4>Costing remains blocked</h4><ul>{current.data.costing_blockers.map(text => <li key={text}>{text}</li>)}</ul>
      <p>{current.data.notice}</p>
      <label htmlFor="interpret-reviewer">Reviewer name</label><input id="interpret-reviewer" value={reviewer} onChange={e => setReviewer(e.target.value)} maxLength={100} />
      <button type="button" disabled={!reviewer.trim()} onClick={() => persist({ ...current, review: `${reviewer.trim()} acknowledged this draft at ${new Date().toISOString()}. No baseline approval or costing application.` })}>Acknowledge draft review</button>
      {current.review && <p role="status">{current.review}</p>}
      <button type="button" onClick={download}>Download interpretation record</button>
      <p className="muted">Up to 20 current-input equipment drafts are retained in this browser tab. Review acknowledgement is not certification or approval to apply costs.</p>
    </article>}
  </section>;
}
