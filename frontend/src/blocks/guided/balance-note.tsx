'use client';

import { useId, useState } from 'react';
import { list, obj, text } from '@/lib/guided-flow';

/** Displays Python diagnostics only; no balance arithmetic is done in the UI. */
export function BalanceNote({ value }: { value: unknown }) {
  const summary = obj(value);
  const [open, setOpen] = useState(false);
  const id = useId();
  if (!summary.mass) return null;
  const label = (status: unknown) => status === 'verified' ? 'Verified balanced' : status === 'inconsistent'
    ? 'Stream totals are inconsistent' : status === 'imbalanced' ? 'Does not balance' : 'Not yet verified';
  const verified = summary.mass === 'verified' && summary.energy === 'verified';
  const mismatch = list(summary.mismatches);
  return <span className="gf-balance-note" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}
    onKeyDown={(event) => { if (event.key === 'Escape') { setOpen(false); event.stopPropagation(); } }}>
    <button type="button" className="gf-balance-trigger" aria-label="Mass and energy balance notes"
      aria-expanded={open} aria-controls={id} aria-describedby={open ? id : undefined}
      onFocus={(event) => { if (event.currentTarget.matches(':focus-visible')) setOpen(true); }}
      onBlur={() => setOpen(false)} onClick={() => setOpen(true)}>
      <span aria-hidden="true">ⓘ</span> <span>Balance notes{verified ? ' · balanced' : ''}</span>
    </button>
    {open && <span id={id} role="tooltip" className="gf-balance-popover">
      <strong>Mass &amp; energy balance</strong>
      <span><b>Mass:</b> {label(summary.mass)}</span>
      <span><b>Energy:</b> {label(summary.energy)}</span>
      {mismatch.map((item, index) => <span key={`${text(item.source)}-${index}`}>
        Stream {text(item.stream)}: total {text(item.reported)} {text(item.unit)}; components sum to {text(item.component_sum)} {text(item.unit)}. Source: {text(item.source)}.
      </span>)}
      {Array.isArray(summary.notes) && summary.notes.map((note, index) => <span key={index}>{text(note)}</span>)}
      <small>Source values are preserved. These notes do not block your estimate.</small>
    </span>}
  </span>;
}
