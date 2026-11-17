'use client';
import { useState } from 'react';
import {evidenceTarget} from '@/lib/evidence-source-links';
import {AICitations} from './ai-citations';
import { list, obj, strings, text, words, type Row } from '@/lib/guided-flow';

/** Summarise saved provenance only. A reference is not independent verification. */
export function evidencePreview(source: unknown): string {
  if (typeof source === 'string') return source.trim();
  if (Array.isArray(source)) return source.map(evidencePreview).filter(Boolean).join(' · ');
  const record = obj(source);
  return [text(record.reference || record.title || record.filename || record.name || record.url),
    record.printed_page != null ? `printed p. ${text(record.printed_page)}` : '',
    record.pdf_page != null ? `PDF p. ${text(record.pdf_page)}` : '',
  ].filter(Boolean).join(' · ');
}

/** Only an explicit saved web URL can open a document; filenames are citations. */
export function evidenceLink(source: unknown): string | null {
  return evidenceTarget(source)?.url || null;
}

export function SourceDocumentLink({source}:{source:unknown}) {
  const target=evidenceTarget(source);
  if(!target)return null;
  return <a className="gf-evidence-source-link" href={target.url} target="_blank" rel="noopener noreferrer" title={target.note}>{target.label}</a>;
}

function SavedFields({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value == null || value === '') return null;
  if (typeof value !== 'object') {
    const label = String(value);
    return /^https?:\/\/\S+$/i.test(label) ? <a href={label} target="_blank" rel="noopener noreferrer">{label} ↗</a> : <span>{label}</span>;
  }
  if (depth >= 3) return <pre>{JSON.stringify(value, null, 2)}</pre>;
  return <dl>{Object.entries(value).filter(([, v]) => v != null && v !== '').map(([key, item]) => <div key={key}><dt>{words(key)}</dt><dd><SavedFields value={item} depth={depth + 1} /></dd></div>)}</dl>;
}

/** Local disclosure: no fetch, research, polling or model work on hover/open. */
export function EvidenceNote({ note, source, reasoning = [], evidence = [], record, label = 'Basis & evidence', pending = false, aiCitations, aiBasis }: {
  aiCitations?: Row[]; aiBasis?: unknown;
  note?: string; source?: unknown; reasoning?: string[]; evidence?: string[]; record?: Row; label?: string; pending?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const preview = evidencePreview(source);
  const target = evidenceTarget(source);
  const hint = preview || (evidence.length ? `Saved references: ${evidence.join(', ')}` : 'No source citation is attached to this saved note.');
  if (!note && !preview && !reasoning.length && !evidence.length && !record) return null;
  return <div className="gf-evidence-wrap"><details className="gf-evidence-note" onToggle={(e) => setOpen(e.currentTarget.open)} onKeyDown={(e) => {
    if (e.key === 'Escape') { e.currentTarget.open = false; e.currentTarget.querySelector('summary')?.focus(); }
  }}>
    <summary>
      <span className="gf-evidence-symbol" aria-hidden="true">✧</span>
      <span className="gf-evidence-copy"><span className="gf-evidence-label">{label}<span aria-hidden="true"> ↗</span></span>{note && <span className="gf-evidence-teaser">{note}</span>}</span>
      <span className="gf-evidence-badge">{preview ? 'View citation' : evidence.length ? `${evidence.length} references` : 'Source not attached'}</span>
      <span className="gf-evidence-hover" aria-hidden="true"><b>Saved evidence</b>{hint}<em>Click to open evidence & reasoning</em></span>
    </summary>
    <div className="gf-evidence-body">
      {note && <p>{note}</p>}
      {reasoning.length > 0 && <div><strong>Saved AI proposal{pending ? ' · awaiting application' : ''}</strong><ul>{reasoning.map((r, i) => <li key={i}>{r}</li>)}</ul><small>Reasoning is an assumption to review; it is not independent source verification.</small></div>}
      <div><strong>Where this came from</strong><p>{preview || (evidence.length ? 'References named in the saved analysis; identifiers alone are not external citations.' : 'No source citation is attached. Treat this as an unsupported assumption until reviewed.')}</p>{target ? <><SourceDocumentLink source={source}/><small>{target.note}</small></> : preview ? <small>Source access unavailable: no source URL was saved with this reference.</small> : null}</div>
      {evidence.length > 0 && <ul className="gf-evidence-refs">{evidence.map((item, i) => <li key={i}>{item}</li>)}</ul>}
      {open && record && <details className="gf-evidence-record"><summary>Inspect saved source & calculation record</summary><SavedFields value={record} /></details>}
    </div>
  </details>{target && <div className="gf-evidence-direct"><SourceDocumentLink source={source}/><small>Recorded source URL</small></div>}{aiCitations && <AICitations citations={aiCitations} basis={aiBasis}/>}</div>;
}

export function CapexEvidenceNote({ line, config, analyst, factor, origin }: { line: Row; config: Row; analyst: Row; factor: Row; origin: string }) {
  const id = text(line.id);
  const proposal = list(analyst.factors).find((f) => f.id === id);
  return <EvidenceNote note={text(line.rationale)} source={line.source || factor.source}
    aiCitations={proposal ? list(proposal.citations) : undefined} aiBasis={proposal?.basis}
    reasoning={strings(proposal?.reasoning)} pending={analyst.pending_application === true}
    record={{ calculated_line: line, published_factor: factor, saved_ai_proposal: proposal,
      proposal_status: analyst.stale ? 'Earlier analysis · stale' : analyst.pending_application ? 'Awaiting application' : 'Saved proposal; compare with current selection',
      selection_origin: origin, selected_fraction: obj(config.selected_factors)[id], override: obj(config.overrides)[id] }} />;
}
