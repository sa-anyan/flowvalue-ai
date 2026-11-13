'use client';
import {useState} from 'react';

type Evidence = {id?:string;workbook?:string;sheet?:string;cell?:string;property?:string;component?:string;original_value?:unknown;original_unit?:string;normalized_value?:unknown;normalized_unit?:string;status?:string;note?:string;formula?:string;cached?:boolean};
type Entity = {key:string;kind:string;identifier:string;case?:string;id_evidence?:Evidence;values:Evidence[]};
type Report = {entities:Entity[];issues?:{code:string;message?:string}[];connections?:{role:string;status?:string;basis?:string}[]};
const shown=(value:unknown)=>value===null||value===undefined?'Missing':String(value);
const status=(value:Evidence)=>value.status==='verified'&&value.original_value!==null&&value.original_value!==undefined&&value.normalized_value!==null&&value.normalized_value!==undefined?'Source-supported · review before use':'Needs review';

export function MappingPreview({report}:{report:Report}){
 const [onlyReview,setOnlyReview]=useState(false);
 const rows=report.entities.flatMap(entity=>[entity.id_evidence,...entity.values].filter((value):value is Evidence=>Boolean(value)).map(value=>({entity,value})));
 const filtered=onlyReview?rows.filter(row=>status(row.value)==='Needs review'):rows;
 const unresolved=rows.filter(row=>status(row.value)==='Needs review').length;
 const duplicates=new Map<string,number>();
 for(const entity of report.entities){const key=[entity.kind,entity.case||'',entity.identifier].join(' / ');duplicates.set(key,(duplicates.get(key)||0)+1);}
 const repeated=[...duplicates.entries()].filter(([,count])=>count>1);
 return <section className="equipment-explorer" aria-label="Read-only source mapping preview">
  <div className="explorer-heading"><div><h2>Source mapping preview</h2><p>Original workbook observations beside extracted canonical candidates. This preview does not save, approve, or modify engineering data.</p></div></div>
  <p className="data-caution">“Source-supported” means the workbook contains supporting evidence; it is not certification of plant measurements, conversion assumptions or physical connectivity.</p>
  <div className="register-stats"><div><strong>{rows.length}</strong><span>Observations</span></div><div><strong>{unresolved}</strong><span>Require review</span></div><div><strong>{report.issues?.length||0}</strong><span>Parser issues</span></div><div><strong>{repeated.length}</strong><span>Repeated display tags</span></div></div>
  <label className="check"><input type="checkbox" checked={onlyReview} onChange={event=>setOnlyReview(event.target.checked)}/>Show observations requiring review only</label>
  {repeated.length>0&&<details><summary>Repeated display tags ({repeated.length})</summary><ul>{repeated.map(([key,count])=><li key={key}>{key} · {count} separate records; keys remain distinct</li>)}</ul></details>}
  {!!report.issues?.length&&<details><summary>Source parsing issues ({report.issues.length})</summary><ul>{report.issues.map((issue,index)=><li key={index}>{issue.code}: {issue.message||'Review original source evidence'}</li>)}</ul></details>}
  {!!report.connections?.length&&<p className="data-caution">{report.connections.length} recorded connection associations are available for inspection. This preview does not verify any physical piping, including explicit-field records.</p>}
  <div className="table-wrap"><table><thead><tr><th>Canonical record / scope</th><th>Property</th><th>Original observation</th><th>Extracted candidate</th><th>Source</th><th>Interpretation</th></tr></thead><tbody>
  {filtered.map(({entity,value},index)=><tr key={entity.key+':'+(value.id||index)}><td>{entity.identifier}<small> · {entity.kind} · {entity.case||'case not declared'}</small></td><td>{shown(value.property)}{value.component?' · '+value.component:''}</td><td>{shown(value.original_value)} {value.original_unit||''}</td><td>{shown(value.normalized_value)} {value.normalized_unit||''}</td><td>{shown(value.workbook)} · {shown(value.sheet)}!{shown(value.cell)}</td><td>{status(value)}{value.formula&&<small> · formula present; cached: {value.cached?'yes':'no'}</small>}{value.note&&<small> · {value.note}</small>}</td></tr>)}
  {!filtered.length&&<tr><td colSpan={6}>No observations match this filter.</td></tr>}
  </tbody></table></div>
  <p className="data-caution">No mapping decisions are recorded here. Use the existing engineering review and approval workflow separately; unresolved fields require source confirmation.</p>
 </section>;
}
