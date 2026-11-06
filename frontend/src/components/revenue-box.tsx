'use client';

/** One commercial input, shared by initial upload and subsequent interpretation. */
export function RevenueBox({text,onText,busy=false}: {
  text:string; onText:(value:string)=>void; busy?:boolean;
}) {
  return <div>
    <h2>Revenue Box</h2>
    <p>Only the payment sources you state here can feed revenue. Process outputs do not automatically become sales.</p>
    <label className="field"><span>How will this project earn revenue?</span><textarea value={text} disabled={busy} maxLength={6000} onChange={e=>onText(e.target.value)} placeholder="For example: lignin sales at an agreed price, wastewater treatment fees, or both. Include prices and units if known."/></label>
    <p className="muted">Submitting this box requests a fresh AI interpretation. API usage charges apply. Review and approve the proposed assumptions before calculating.</p>
  </div>;
}
