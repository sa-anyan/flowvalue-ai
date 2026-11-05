'use client';
import Link from 'next/link';
import {assessmentHref} from '@/lib/assessment-navigation';
export const isolatedStages=[
  {id:'engineering_data',label:'Engineering data',page:'/data/equipment',requires:[]},
  {id:'equipment',label:'Equipment',page:'/capex/equipment',requires:['engineering_data']},
  {id:'capex',label:'CAPEX',page:'/capex',requires:['equipment']},
  {id:'revenue',label:'Revenue',page:'/revenue',requires:['engineering_data']},
  {id:'opex',label:'OPEX',page:'/opex',requires:['engineering_data']},
  {id:'financial',label:'Financial model',page:'/financial-modelling',requires:['capex','revenue','opex']},
] as const;
export type StageReceipt={status:string;requires?:string[];message?:string;complete?:boolean};
export type StageDefinition={id:string;label:string;page:string;requires:string[]};
export function StageControls({id,receipts,definitions,busy,useAI,onAI,onRun,current,omitEngineering=false}:{
  id:string;receipts:Record<string,StageReceipt>;definitions?:StageDefinition[];busy:boolean;useAI:boolean;
  onAI:(value:boolean)=>void;onRun:(stage:string)=>void;current?:string;omitEngineering?:boolean;
}){
 const stages=definitions?.length?definitions:isolatedStages;
 const label=(key:string)=>stages.find(s=>s.id===key)?.label||key;
 return <section className="stage-controls" aria-label="Independent stage controls">
  <h2>{omitEngineering?'Run remaining stages individually':'Run stages individually'}</h2>
  <p>Only the stage you choose will run. Required data must already exist; missing stages are never run automatically.</p>
  <label className="check"><input type="checkbox" checked={useAI} disabled={busy} onChange={e=>onAI(e.target.checked)}/>Use AI proposals for the selected stage (usage charges apply)</label>
  <div className="stage-control-grid">{stages.filter(s=>(!current||s.id===current)&&(!omitEngineering||!['engineering_data','equipment'].includes(s.id))).map(s=>{
   const receipt=receipts[s.id],status=receipt?.status||'not_run';
   return <article key={s.id} className="stage-control-card">
    <div className="toolbar"><strong>{s.label}</strong><span className="badge">{status==='ready'?(receipt?.complete===false?'Partial output':'Output available'):status==='stale'?'Rerun required':status==='data_required'?'Data required':status==='running'?'Running':'Not run'}</span></div>
    <small>{s.requires.length?'Requires: '+s.requires.map(label).join(', '):'Requires: uploaded workbook'}</small>
    {receipt?.message&&<p role="status">{receipt.message}</p>}
    <div className="toolbar"><button disabled={busy||!id} onClick={()=>onRun(s.id)}>Run {s.label}</button>{id&&<Link href={assessmentHref(s.page,id)}>Open stage →</Link>}</div>
   </article>;
  })}</div>
 </section>;
}
