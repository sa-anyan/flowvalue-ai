"use client";

import Link from "next/link";
import { EquipmentInterpretation, type InterpretationRecords } from "./equipment-interpretation";
import { apiFetch } from "@/lib/client-api";
import { useEffect, useState } from "react";
import type { BalanceReport, BalanceEvidence } from "@/lib/balance";

type CatalogItem = { id: string; name: string; pdf_page: number; printed_page: number; cost_method_status: string; source_refs: { source_id: string; pdf_page: number; printed_page: number }[] };
type CatalogSource = { id: string; label: string; filename: string; index_basis: { series: string; value: number; period: string; pdf_page: number; printed_page: number } };
type Catalog = { sources: CatalogSource[]; version: string; equipment: CatalogItem[]; source: { title: string; author: string; year: number } };
type MatchResult = {
  equipment_key: string; tag: string; sheet: string; case: string;
  status: "match" | "review" | "no_match"; reason: string; descriptions: string[];
  candidates: CatalogItem[]; evidence: BalanceEvidence[]; tag_source: BalanceEvidence;
};
type Matches = { catalog_version: string; results: MatchResult[]; notice: string };

export function EquipmentCatalogMatches({ report, processDescription = "" }: { report: BalanceReport | null; processDescription?: string }) {
  const [interpretations, setInterpretations] = useState<InterpretationRecords | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [state, setState] = useState<{ report: BalanceReport; data?: Matches; error?: string } | null>(null);
  const [catalogError, setCatalogError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    apiFetch("/api/equipment/catalog", { signal: controller.signal }).then(async (response) => {
      if (!response.ok) throw new Error("Equipment catalog unavailable");
      const data: Catalog = await response.json();
      if (!controller.signal.aborted) { setCatalog(data); setCatalogError(""); }
    }).catch((error: Error) => { if (!controller.signal.aborted) setCatalogError(error.message); });
    return () => controller.abort();
  }, [retry]);
  useEffect(() => {
    if (!report) return;
    const controller = new AbortController();
    apiFetch("/api/equipment/match", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(report), signal: controller.signal,
    }).then(async (response) => {
      if (!response.ok) throw new Error("Equipment matching failed. Your parsed workbook is unchanged.");
      const data: Matches = await response.json();
      if (!controller.signal.aborted) setState({ report, data });
    }).catch((error: Error) => { if (!controller.signal.aborted) setState({ report, error: error.message }); });
    return () => controller.abort();
  }, [report, retry]);
  const sourceLabel = (id: string) => catalog?.sources.find(source => source.id === id)?.label ?? id;
  const current = state?.report === report ? state : null;
  const aiRecords = interpretations?.report === report && interpretations.description === processDescription ? interpretations.records : [];
  return <><section className="panel equipment-catalog" aria-label="Equipment catalog matching">
    <div className="panel-heading"><h1>Detected equipment &amp; catalog matches</h1><Link href="/entry">Upload workbook</Link></div>
    <p className="muted">{catalog ? `${catalog.equipment.length} chart groups · ${catalog.sources.length} source files · ${catalog.source.author}, ${catalog.source.year}` : "Loading equipment catalog…"}</p>
    <p className="muted">Names only. A match identifies a catalog entry; it does not validate a cost curve or calculate a price.</p>
    {catalogError && <p role="alert">{catalogError} <button type="button" onClick={() => setRetry(x => x + 1)}>Retry</button></p>}
    {!report ? <p>Upload a mass and energy balance on Entry to match its detected equipment.</p> : <>
      <p>{report.filename}</p>
      {!current && <p role="status">Checking detected equipment…</p>}
      {current?.error && <p role="alert">{current.error} <button type="button" onClick={() => setRetry(x => x + 1)}>Retry</button></p>}
      {current?.data && (current.data.results.length ? <div className="table-scroll"><table>
        <thead><tr><th>Detected equipment</th><th>Catalog status</th><th>Equipment cost catalog</th><th>Why this match?</th><th>Workbook evidence</th></tr></thead>
        <tbody>{current.data.results.map(item => {
          const ai = aiRecords.find(record => record.data.equipment_key === item.equipment_key)?.data;
          return <tr key={item.equipment_key}>
          <th scope="row">{item.tag}<small className="block">{item.sheet}{item.case ? ` · ${item.case}` : ""}</small></th>
          <td><strong className="equipment-catalog-status" data-status={ai ? "review" : item.status} title={item.reason}>{ai ? "AI proposal · review" : item.status === "match" ? "Name match" : item.status === "review" ? "Candidate · review" : "Type unresolved"}</strong></td>
          <td>{ai ? <>{ai.draft.candidates.length ? ai.draft.candidates.map(candidate => <div key={candidate.catalog_id}><strong>{ai.candidate_sources.find(source => source.id === candidate.catalog_id)?.name ?? candidate.catalog_id}</strong><small className="block">Provisional costing basis</small>{ai.candidate_sources.find(source => source.id === candidate.catalog_id)?.source_refs.map(ref => <small className="block" key={ref.source_id}>{ref.label ?? sourceLabel(ref.source_id)} · p. {ref.printed_page}</small>)}</div>) : "No supported AI candidate"}<small className="block">{ai.draft.interpreted_identity}</small></> : item.candidates.length ? item.candidates.map(candidate => <div key={candidate.id}>{candidate.name}<small className="block">{candidate.source_refs.map(ref => <span className="block" key={ref.source_id}>{sourceLabel(ref.source_id)} · p. {ref.printed_page} · PDF p. {ref.pdf_page}</span>)}</small></div>) : "Type not established / not in catalog"}</td>
          <td>{ai ? ai.draft.candidates.map(candidate => <p key={candidate.catalog_id}>{candidate.rationale}</p>) : <><p>{item.descriptions.length ? `Workbook wording: ${item.descriptions.join("; ")}. ` : ""}{item.reason}</p>{item.status === "no_match" && <small className="block">Use AI interpretation below to investigate a functional analogue.</small>}</>}</td>
          <td><details><summary>{item.tag_source.sheet}!{item.tag_source.cell}</summary>{item.descriptions.map(text => <div key={text}>{text}</div>)}{(item.evidence.length ? item.evidence : [item.tag_source]).map(evidence => <small key={evidence.id} className="block">{evidence.sheet}!{evidence.cell} · {String(evidence.original_value ?? "")}</small>)}<small className="block">{item.reason}</small></details></td>
        </tr>; })}</tbody>
      </table></div> : <p>No equipment identified in this workbook. No catalog matches can be established.</p>)}
    </>}
    {catalog && <details style={{ marginTop: 20 }}><summary>Sources &amp; historical index bases</summary>{catalog.sources.map(source => <p key={source.id}><strong>{source.label}</strong><small className="block">{source.filename}</small><small className="block">{source.index_basis.series}: {source.index_basis.value} · {source.index_basis.period} · p. {source.index_basis.printed_page} / PDF p. {source.index_basis.pdf_page}</small></p>)}<p className="muted">Source-specific historical bases are retained separately. They do not replace the current model’s index settings.</p></details>}
    {catalog && <details style={{ marginTop: 20 }}><summary>Equipment cost catalog · {catalog.equipment.length} chart groups</summary><div className="table-scroll"><table>
      <thead><tr><th>Equipment / capital item</th><th>Source references</th></tr></thead>
      <tbody>{catalog.equipment.map(item => <tr key={item.id}><td>{item.name}</td><td>{item.source_refs.map(ref => <small className="block" key={ref.source_id}>{sourceLabel(ref.source_id)} · p. {ref.printed_page} · PDF p. {ref.pdf_page}</small>)}</td></tr>)}</tbody>
    </table></div></details>}
  </section><EquipmentInterpretation report={report} processDescription={processDescription} onRecords={setInterpretations} /></>;
}
