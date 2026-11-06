'use client';
import {useState} from 'react';
type Entry={equipment_key:string;tag:string;retained_tag:string;reason:string;status:string;source?:{sheet?:string;cell?:string};notice?:string};
export function DuplicateReview({entries,busy,dirty,onDecision}:{entries:Entry[];busy:boolean;dirty:boolean;onDecision:(key:string,restore:boolean)=>void}){
 const [open,setOpen]=useState(false);
 const dropped=entries.filter(e=>e.status==='dropped').length;
 return <section aria-label="Equipment removals" style={{padding:'16px 20px'}}>
  <button type="button" className="secondary" aria-expanded={open} aria-controls="equipment-drops" onClick={()=>setOpen(!open)}>Review drops & removals{dropped?` · ${dropped}`:''}</button>
  {open&&<div id="equipment-drops"><p>Identical tags are combined. When both a plain tag and its AB tag exist, the AB entry is retained as two units. Original source records remain available.</p>
   {dirty&&<p role="status">Save or discard your equipment edits before changing removals.</p>}
   {!entries.length&&<p>No duplicate equipment entries were removed in this run.</p>}
   {entries.map(e=><article key={e.equipment_key} style={{borderTop:'1px solid var(--border, #dce3dd)',padding:'12px 0'}}><strong>{e.tag}</strong><p>{e.status==='restored'?'Restored as a separate entry':'Excluded from pricing'} · represented by {e.retained_tag}</p><p>{e.reason}</p>{e.source?.sheet&&<small>Source: {e.source.sheet}{e.source.cell?'!'+e.source.cell:''}</small>}<p><small>{e.notice}</small></p><button type="button" className="secondary" disabled={busy||dirty} onClick={()=>onDecision(e.equipment_key,e.status!=='restored')}>{e.status==='restored'?'Exclude duplicate again':'Add back as separate equipment'}</button></article>)}
   <small>Adding back runs Equipment with saved inputs and no AI call. Other stages may need recalculation.</small>
  </div>}
 </section>;
}
