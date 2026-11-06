'use client';
import {RevenueBox} from './revenue-box';

type Row = Record<string, unknown>;
function row(value: unknown): Row { return value && typeof value === 'object' && !Array.isArray(value) ? value as Row : {}; }
function rows(value: unknown): Row[] { return Array.isArray(value) ? value.map(row) : []; }

export function RevenueApproval({text,onText,config,questions,approved,busy,dirty,onSave,onApprove}: {
  text:string; onText:(value:string)=>void; config:unknown; questions:string[]; approved:boolean;
  busy:boolean; dirty:boolean; onSave:()=>void; onApprove:()=>void;
}) {
  const c=row(config), schedule=row(c.operating);
  const pending=rows(c.pending_inputs);
  const payments=[...rows(c.sales).map(s=>({name:s.name,stream:s.stream_key,unit:s.quantity_unit,price:s.price_mode==='assumed_price'?s.unit_price:'Price required'})),
    ...rows(c.commercial_lines).map(s=>({name:s.name,stream:s.stream_key||'Contract quantity',unit:s.quantity_unit,price:row(rows(s.years)[0]).rate}))];
  return <section aria-label="Revenue Box and approval">
    <RevenueBox text={text} onText={onText} busy={busy}/>
    <button className="secondary" disabled={busy||!text.trim()} onClick={onSave}>{busy?'Interpreting revenue…':'Save & interpret with AI'}</button>
    {questions.length>0&&<ul aria-label="Revenue clarification questions">{questions.map(q=><li key={q}>{q}</li>)}</ul>}
    {pending.length>0&&<details open><summary>Pending commercial inputs</summary>{pending.map((p,i)=><div key={i}><h3>{String(p.name??'Pending opportunity')}</h3><p>{String(p.category??'').replaceAll('_',' ')} · {String(p.rate??'Rate needed')} {String(p.rate_unit??'')}</p><p>{String(p.quantity_basis??'')}</p><blockquote>{String(p.context_quote??'')}</blockquote><small>Not included in calculated income or savings until the missing inputs are resolved.</small></div>)}</details>}
    <details open><summary>Review saved commercial assumptions</summary>
      <p>{String(schedule.days_per_year??'Missing')} days/year · {String(schedule.hours_per_day??'Missing')} hours/day · {String(row(c.price_basis).currency??'Currency missing')}</p>
      {payments.map((p,i)=><p key={i}><strong>{String(p.name??'Unnamed payment')}</strong> · {String(p.price??'Price required')} per {String(p.unit??'unit required')} · Stream: {String(p.stream??'Mapping required')}</p>)}
      <p>Review annual terms, sales fractions, stream mappings and prices in the editable assumptions below. Save edits before approval.</p>
    </details>
    {dirty&&<p className="notice">Save your Revenue Box and assumption edits before approving.</p>}
    <button disabled={busy||dirty||!payments.length||!text.trim()} onClick={onApprove}>Approve saved revenue assumptions &amp; calculate</button>
    <p role="status">{approved?'These saved revenue assumptions have been approved. Revenue-related changes require fresh approval.':'Revenue is a draft. It will not feed financial calculations until you approve it.'}</p>
  </section>;
}
