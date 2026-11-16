'use client';
import {useState} from 'react';
import {CalculationBreakdown} from './calculation-breakdown';
import type {Row} from '@/lib/monte-carlo';
const obj=(v:unknown):Row=>v&&typeof v==='object'&&!Array.isArray(v)?v as Row:{};
const rows=(v:unknown):Row[]=>Array.isArray(v)?v.map(obj):[];
const label=(v:string)=>v.replaceAll('_',' ');
const money=(v:unknown)=>v===null||v===undefined?'Not available':new Intl.NumberFormat('en-GB',{maximumFractionDigits:2}).format(Number(v));
const display=(v:unknown)=>v===null||v===undefined?'Not supplied':typeof v==='object'?JSON.stringify(v):String(v);
export type MetricFilter={metric:string;low:number;high:number;includeHigh:boolean};
export function visibleRuns(runs:Row[],status:string,query:string,metric:MetricFilter|null,indices:number[]|null) {
 return runs.filter(run=>{
  if((status!=='all'&&run.status!==status)||(indices&&!indices.includes(Number(run.index)))||(query&&!JSON.stringify({index:run.index,samples:run.samples}).toLowerCase().includes(query.toLowerCase())))return false;
  if(!metric)return true;
  const equipment=metric.metric.startsWith('equipment:');
  const value=equipment?obj(run.equipment_costs)[metric.metric.slice(10)]:obj(run.metrics)[metric.metric];
  const eligible=equipment?run.status!=='failed'&&value!==null&&value!==undefined:Array.isArray(run.metric_eligible)&&run.metric_eligible.includes(metric.metric);
  return eligible&&Number(value)>=metric.low&&(metric.includeHigh?Number(value)<=metric.high:Number(value)<metric.high);
 });
}
export function RunExplorer({runs,filter,indices,onClear,onInspect}:{runs:Row[];filter:MetricFilter|null;indices:number[]|null;onClear:()=>void;onInspect:(index:number)=>void}) {
 const [query,setQuery]=useState(''),[status,setStatus]=useState('all'),[sort,setSort]=useState('index'),[limit,setLimit]=useState(25);
 const shown=visibleRuns(runs,status,query,filter,indices).sort((a,b)=>sort==='index'?Number(a.index)-Number(b.index):Number(obj(a.metrics)[sort]??Infinity)-Number(obj(b.metrics)[sort]??Infinity));
 return <section className="mc-card" aria-label="Explore individual variations"><h2>Explore individual variations</h2><p>Select a row to inspect every applied input, exact equipment model, cost breakdown and cash-flow result. Runs with unresolved or invalid calculations remain visible.</p>
 <div className="toolbar"><label>Find run or sampled value<input aria-label="Find variation" value={query} onChange={e=>{setQuery(e.target.value);setLimit(25);}}/></label><label>Status<select value={status} onChange={e=>setStatus(e.target.value)}>{['all','complete','partial','failed'].map(s=><option key={s}>{s}</option>)}</select></label><label>Sort by<select value={sort} onChange={e=>setSort(e.target.value)}>{['index','npv','capex','opex','revenue'].map(s=><option key={s}>{s}</option>)}</select></label>{(filter||indices)&&<button className="secondary" onClick={onClear}>Clear chart / sensitivity filter</button>}</div>
 <p role="status">{shown.length} of {runs.length} variations{filter?` · ${filter.metric} from ${filter.low} to ${filter.high}`:''}{indices?' · selected sensitivity group':''}</p>
 <div className="mc-matrix-scroll mc-table-viewport"><table className="mc-matrix mc-run-table"><thead><tr>{['Variation','Status','NPV','CAPEX','OPEX','Revenue'].map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{shown.slice(0,limit).map(run=><tr key={String(run.index)}><th><button className="secondary" title={`Status: ${run.status}. NPV: ${money(obj(run.metrics).npv)}. Click for the exact configuration.`} onClick={()=>onInspect(Number(run.index))}>Inspect variation {Number(run.index)+1}</button></th><td>{String(run.status)}</td>{['npv','capex','opex','revenue'].map(k=><td key={k}>{money(obj(run.metrics)[k])}</td>)}</tr>)}</tbody></table></div>
 {shown.length>limit&&<button className="secondary" onClick={()=>setLimit(limit+25)}>Show 25 more variations</button>}
 </section>;
}
function InputTree({value,names={}}:{value:unknown;names?:Record<string,string>}) {
 if(value===null||typeof value!=='object')return <span className="mc-config-values">{display(value)}</span>;
 return <dl>{Object.entries(value).map(([key,v])=><div key={key}><dt>{Array.isArray(value)?String(names[String(obj(v).equipment_key)]||obj(v).name||obj(v).role||obj(v).id||(obj(v).year!==undefined?`Year ${obj(v).year}`:key)):label(key)}</dt><dd>{v!==null&&typeof v==='object'?<details><summary>{Array.isArray(v)?`${v.length} records`:'Inspect values'}</summary><InputTree value={v} names={names}/></details>:<span className="mc-config-values">{display(v)}</span>}</dd></div>)}</dl>;
}
export function RunConfiguration({run,id,jobId}:{run:Row;id:string;jobId:string}) {
 const config=obj(run.configuration),plan=obj(config.plan),operating=obj(plan.operating_economics);
 const names=Object.fromEntries(rows(run.equipment_records).map(record=>[String(record.record_key),String(record.display_tag)]));
 const sections: [string,unknown][]=[['Equipment configurations and inputs',plan.equipment],['CAPEX method and factors',plan.capex],['OPEX materials',operating.materials],['Utilities and energy',operating.energy],['Operating labour',operating.labour],['OPEX factors',operating.garrett_factors],['Additional operating expenses',operating.additional_expenses],['Revenue products',operating.sales],['Commercial revenue',operating.commercial_lines],['Avoided costs',operating.avoided_costs],['Operating schedule',operating.operating],['Financial assumptions',operating.financial],['Price basis',operating.price_basis],['Cost translation',plan.cost_translation]];
 return <section className="mc-card" aria-label="Variation configuration"><h2>Variation {Number(run.index)+1} · complete configuration</h2><small>{String(run.status)} · seed {display(config.seed)} · baseline revision {display(config.baseline_revision)}</small>
 <div className="mc-kpis">{[['Project NPV','npv'],['CAPEX','capex'],['Annual OPEX','opex'],['Annual revenue','revenue']].map(([title,key])=><div key={key}><small>{title}</small><strong>{money(obj(run.metrics)[key])}</strong></div>)}</div>
 <CalculationBreakdown key={String(run.index)} run={run}/>
 <details><summary>Selected inputs: baseline versus applied value</summary><div className="mc-matrix-scroll"><table className="mc-matrix"><thead><tr><th>Parameter</th><th>Baseline</th><th>This variation</th><th>Units</th></tr></thead><tbody>{rows(config.parameters).filter(p=>p.enabled).flatMap(p=>rows(p.values).map((v,i)=><tr key={String(p.id)+i}><th>{String(p.label)}</th><td>{display(v.baseline)}</td><td>{display(v.applied)}</td><td>{String(p.unit)}</td></tr>))}</tbody></table></div>
 </details>
 <h3>All configuration inputs, including those held fixed</h3><div className="mc-config-groups">{sections.filter(([,v])=>v!==undefined).map(([title,value])=><details key={title}><summary>{title}</summary><InputTree value={value} names={names}/></details>)}</div>
 <details><summary>All saved study settings, ranges, weights and dependencies</summary><InputTree value={config.study_settings}/></details>
 <details><summary>Provenance, full source record and download</summary><p>{String(config.notice||'Saved historical outputs; full configuration may be unavailable.')}</p><small className="mc-config-values">Configuration fingerprint: {display(config.hash)} · {config.fingerprint_verified?'verified against the calculated draw':'historical result: no original draw fingerprint'}</small><p><a className="report-link" download href={`/api/assessments/${id}/monte-carlo/jobs/${jobId}/runs/${run.index}?download=true`}>Download full variation configuration (JSON)</a></p><pre className="mc-json">{JSON.stringify(config,null,2)}</pre></details>
 <details><summary>Technical calculation records</summary>{['metrics','equipment_records','capex_components','opex_components','cash_flow','unpriced','invalid_calculations','issues','metric_status'].map(field=><details key={field}><summary>{label(field)}</summary><pre className="mc-json">{JSON.stringify(run[field],null,2)}</pre></details>)}</details>
 </section>;
}
