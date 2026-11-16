'use client';
import {useEffect,useId,useRef,useState} from 'react';
import {Histogram} from './histogram';
import {AnalysisDrawer} from './analysis-drawer';
import {RunExplorer,RunConfiguration,type MetricFilter} from './run-explorer';
import {mcApi,type Job,type Row} from '@/lib/monte-carlo';
const object=(v:unknown):Row=>v&&typeof v==='object'&&!Array.isArray(v)?v as Row:{};
const rows=(v:unknown):Row[]=>Array.isArray(v)?v.map(object):[];
const num=(v:unknown)=>v===null||v===undefined||!Number.isFinite(Number(v))?null:Number(v);
const format=(v:unknown,percent=false)=>num(v)===null?'—':percent?(Number(v)*100).toFixed(1)+'%':new Intl.NumberFormat('en-GB',{notation:'compact',maximumFractionDigits:2}).format(Number(v));
function CashFlowFan({data}:{data:Row[]}){const values=data.filter(d=>num(object(d.fcff).p10)!==null&&num(object(d.fcff).p90)!==null);if(values.length<2)return null;const lo=Math.min(0,...values.map(d=>Number(object(d.fcff).p10))),hi=Math.max(0,...values.map(d=>Number(object(d.fcff).p90))),range=hi-lo||1;const x=(i:number)=>30+i/(values.length-1)*660,y=(v:number)=>180-(v-lo)/range*150;const lower=values.map((d,i)=>`${x(i)},${y(Number(object(d.fcff).p10))}`),upper=values.map((d,i)=>`${x(i)},${y(Number(object(d.fcff).p90))}`).reverse();return <><svg className="mc-cash-fan" viewBox="0 0 720 215" role="img" aria-label="Pointwise P10 to P90 cash-flow band and median by project year"><line x1="30" x2="690" y1={y(0)} y2={y(0)} stroke="#a8b7af"/><polygon points={[...lower,...upper].join(' ')} fill="#3578bd30"/><polyline points={values.map((d,i)=>`${x(i)},${y(Number(object(d.fcff).p50))}`).join(' ')} fill="none" stroke="#3578bd" strokeWidth="2.5"/>{values.map((d,i)=><circle key={i} cx={x(i)} cy={y(Number(object(d.fcff).p50))} r="3" fill="#3578bd"><title>Year {String(d.year)} · P50 {format(object(d.fcff).p50)}</title></circle>)}<text x="30" y="208" fontSize="11" fill="currentColor">Year {String(values[0].year)}</text><text x="625" y="208" fontSize="11" fill="currentColor">Year {String(values.at(-1)?.year)}</text></svg><small>Pointwise P10–P90 envelope with median line; not a simultaneous confidence band.</small></>;}
function SensitivityRow({driver,max,onInspect}:{driver:Row;max:number;onInspect:()=>void}) {
 const [hover,setHover]=useState(false),tip=useId();
 return <div className="mc-hover-shell"><button type="button" className="mc-driver mc-driver-inspect" aria-label={`Inspect sensitivity ${driver.label} ${driver.metric}`} aria-describedby={hover?tip:undefined} onMouseEnter={()=>setHover(true)} onMouseLeave={()=>setHover(false)} onFocus={()=>setHover(true)} onBlur={()=>setHover(false)} onClick={()=>{setHover(false);onInspect();}}>
  <div><strong>{String(driver.label)}</strong><small>{String(driver.metric).toUpperCase()} · {driver.spearman===null?'Configuration comparison':`Rank association ${Number(driver.spearman).toFixed(2)}`}</small></div>
  <div className="mc-driver-track"><b className="mc-driver-center"/>{[Number(driver.low_effect??-Number(driver.span)/2),Number(driver.high_effect??Number(driver.span)/2)].map((effect,i)=><i key={i} style={{left:(50+Math.min(0,effect)/max*50)+'%',width:Math.max(.5,Math.abs(effect)/max*50)+'%',top:i===0?'3px':'13px',background:i===0?'#c99b52':'#3d83a5'}}/>)}</div><span>{format(driver.low_group_median)} → {format(driver.high_group_median)}</span>
 </button>{hover&&<span id={tip} role="tooltip" className="mc-hover-info"><strong>{String(driver.label)}</strong><span>Low-group median: {format(driver.low_group_median)}</span><span>High-group median: {format(driver.high_group_median)}</span><span>Conditional association, not a causal effect. Click to inspect the saved setup and exact contributing variations.</span></span>}</div>;
}
export function MonteResults({id,job,jobs,onSelect}:{id:string;job:Job|null;jobs:Job[];onSelect:(id:string)=>void}) {
 const [indexRows,setIndexRows]=useState<Row[]>([]),[filter,setFilter]=useState<MetricFilter|null>(null),[sensitivity,setSensitivity]=useState<Row|null>(null),[groupIndices,setGroupIndices]=useState<number[]|null>(null);
 const [view,setView]=useState('overview'),[metric,setMetric]=useState('npv'),[drawerOpen,setDrawerOpen]=useState(false),[drawerView,setDrawerView]=useState<'runs'|'configuration'>('runs');
 const request=useRef(0);
 const [inspecting,setInspecting]=useState<number|null>(null),[representative,setRepresentative]=useState<Row|null>(null),[error,setError]=useState(''),[comparison,setComparison]=useState(''),[audit,setAudit]=useState<Row|null>(null);
 useEffect(()=>{
  let disposed=false;request.current++;setDrawerOpen(false);setInspecting(null);setRepresentative(null);setAudit(null);setIndexRows([]);setFilter(null);setGroupIndices(null);setSensitivity(null);setError('');setView('overview');
  if(job?.summary){
   void mcApi(`assessments/${id}/monte-carlo/jobs/${job.id}/audit`).then(v=>{if(!disposed)setAudit(v);}).catch(e=>{if(!disposed)setError(e.message);});
   void mcApi(`assessments/${id}/monte-carlo/jobs/${job.id}/runs`).then(v=>{if(!disposed)setIndexRows(v);}).catch(e=>{if(!disposed)setError(e.message);});
  }
  return()=>{disposed=true;request.current++;};
 },[id,job?.id,job?.status]);
 const summary=object(job?.summary),metrics=object(summary.metrics),currency=String(summary.currency||'study currency');
 const drivers=rows(summary.drivers),other=jobs.find(j=>j.id===comparison)?.summary;
 function closeDrawer(){request.current++;setDrawerOpen(false);setInspecting(null);setRepresentative(null);setError('');}
 async function inspect(index:number){
  const ticket=++request.current;setDrawerView('configuration');setDrawerOpen(true);setError('');setInspecting(index);setRepresentative(null);
  try{const value=await mcApi(`assessments/${id}/monte-carlo/jobs/${job!.id}/runs/${index}`);if(ticket===request.current)setRepresentative(value);}
  catch(e){if(ticket===request.current)setError((e as Error).message);}
  finally{if(ticket===request.current)setInspecting(null);}
 }
 function openRuns(next:MetricFilter|null=null){request.current++;setInspecting(null);setRepresentative(null);setSensitivity(null);setGroupIndices(null);setFilter(next);setDrawerView('runs');setDrawerOpen(true);setError('');}
 function selectSensitivity(driver:Row){
  setSensitivity(driver);setFilter(null);
  const indices=[...rows(driver.groups).flatMap(g=>Array.isArray(g.runs)?g.runs.map(Number):[]),...(Array.isArray(driver.low_runs)?driver.low_runs.map(Number):[]),...(Array.isArray(driver.high_runs)?driver.high_runs.map(Number):[])];
  setGroupIndices(indices.length?indices:null);
  if(indices.length)void inspect(indices[0]);else if(indexRows.length)void inspect(Number(indexRows[0].index));else{setDrawerView('runs');setDrawerOpen(true);}
 }
 const selector=<div className="mc-results-controls">{jobs.length>0&&<label>Saved study<select value={job?.id||''} onChange={e=>onSelect(e.target.value)}>{jobs.map(j=><option value={j.id} key={j.id}>{j.settings.label} · seed {j.settings.seed} · {j.status}</option>)}</select></label>}{job?.summary&&<p className="muted">{String(summary.attempted)} variations · {currency} · seed {job.settings.seed}</p>}</div>;
 if(!job?.summary)return <>{selector}<section className="mc-card mc-empty">{job&&['running','queued'].includes(job.status)?'Simulation in progress. Results appear after completion.':'Run a simulation from Parameters & setup.'}</section></>;
 const metricOptions=[['npv','Project NPV',currency],['irr','Project IRR','fraction'],['capex','CAPEX',currency],['revenue','Annual revenue',currency+'/year'],['opex','Annual OPEX',currency+'/year'],['known_opex','Known OPEX subtotal',currency+'/year'],['payback','Discounted payback','years'],...Object.entries(object(summary.equipment)).map(([key,value])=>[`equipment:${key}`,`Equipment · ${object(value).display_tag||key}`,currency])];
 const chosen=metricOptions.find(([key])=>key===metric)||metricOptions[0];
 const explore=<RunExplorer runs={indexRows} filter={filter} indices={groupIndices} onClear={()=>{setFilter(null);setGroupIndices(null);setSensitivity(null);}} onInspect={index=>void inspect(index)}/>;
 return <>
  {selector}
  {summary.source_review_required===true&&<p className="error">The calculation library changed during this job. Repeat with a fixed source version before reporting risk probabilities.</p>}
  <div className="mc-view-switch" role="group" aria-label="Analysis view">{[['overview','Overview'],['sensitivities','Sensitivities'],['variations','Variations'],['audit','Audit & exports']].map(([key,name])=><button key={key} type="button" aria-pressed={view===key} onClick={()=>setView(key)}>{name}</button>)}</div>
  {view==='overview'&&<>
   <div className="mc-kpis">{[['Complete variations',`${summary.complete_runs} / ${summary.attempted}`,'All required TEA calculations completed'],['Median NPV',format(object(metrics.npv).p50),currency],['Probability NPV < 0',format(summary.probability_negative_npv,true),'Conditional on selected distributions'],['Median IRR',format(object(metrics.irr).p50,true),'Defined IRRs only']].map(([name,value,note])=><div key={name}><small>{name}</small><strong>{value}</strong><span>{note}</span></div>)}</div>
   <div className="mc-overview-grid"><section className="mc-card"><div className="mc-card-head"><h2>Outcome distribution</h2><label>Metric<select aria-label="Outcome metric" value={metric} onChange={e=>setMetric(e.target.value)}>{metricOptions.map(([key,name])=><option key={key} value={key}>{name}</option>)}</select></label></div><Histogram name={chosen[1]} unit={chosen[2]} value={chosen[0].startsWith('equipment:')?object(object(summary.equipment)[chosen[0].slice(10)]):object(metrics[chosen[0]])} onSelectBin={(low,high,includeHigh)=>openRuns({metric:chosen[0],low,high,includeHigh})}/><small>Hover for values. Click a bar to inspect its variations.</small></section>
   <section className="mc-card"><h2>Cash-flow outlook</h2>{rows(summary.cash_flow).length?<CashFlowFan data={rows(summary.cash_flow)}/>:<p>Complete cash flows are unavailable; inspect scope in Audit.</p>}<h3>Representative configurations</h3><div className="toolbar">{rows(summary.representative_runs).map(r=><button className="secondary" key={String(r.label)} title={`Actual variation ${Number(r.run)+1} closest to ${r.label} NPV. Click for full configuration.`} onClick={()=>{setSensitivity(null);void inspect(Number(r.run));}}>{String(r.label)} · variation {Number(r.run)+1}</button>)}</div><button type="button" className="secondary" onClick={()=>openRuns()}>Explore all {String(indexRows.length||summary.attempted)} variations</button></section></div>
   <details className="mc-card"><summary>Scope and interpretation</summary><p>{String(summary.scope_notice)}</p><p>200 variations are an exploratory sample conditional on the selected assumptions, not calibrated confidence limits.</p><p>{String(summary.percentile_convention)}</p></details>
  </>}
  {view==='sensitivities'&&<section className="mc-card"><h2>What drives the result?</h2><p className="muted">Hover for a summary. Click to inspect the saved setup and exact contributing configurations.</p>{drivers.length?drivers.slice(0,16).map(d=><SensitivityRow key={String(d.parameter)+d.metric} driver={d} max={Math.max(1,...drivers.filter(x=>x.metric===d.metric).flatMap(x=>[Math.abs(Number(x.low_effect??-Number(x.span)/2)),Math.abs(Number(x.high_effect??Number(x.span)/2))]))} onInspect={()=>selectSensitivity(d)}/>):<p>Too few eligible outcomes or no varying inputs. Check the saved study setup.</p>}</section>}
  {view==='variations'&&explore}
  {view==='audit'&&<section className="mc-card"><h2>Report evidence</h2><div className="mc-outcomes"><span>Complete: {String(summary.complete_runs)}</span><span>Partial: {String(summary.partial_runs)}</span><span>Failed: {String(summary.failed_runs)}</span><span>Invalid calculations: {String(summary.runs_with_invalid_calculations||0)}</span><span>Undefined IRR: {String(summary.undefined_irr_runs||0)}</span></div><p>{String(summary.scope_notice)}</p><div className="toolbar">{[['csv','Results CSV'],['xlsx','Excel + configurations'],['json','Reproducible study JSON']].map(([kind,name])=><a className="report-link" key={kind} download href={`/api/assessments/${id}/monte-carlo/jobs/${job.id}/export?format=${kind}`}>{name}</a>)}</div>
   <details><summary>Frozen study setup and ranges</summary><pre className="mc-json">{JSON.stringify(job.settings,null,2)}</pre></details><details><summary>Source records and calculation provenance</summary><pre className="mc-json">{JSON.stringify(audit,null,2)}</pre></details><details><summary>Statistical conventions and limitations</summary><p>{String(summary.percentile_convention)}</p><p>{String(summary.correlation_convention)}</p><p>Quantiles and probabilities are conditional on the selected distributions and dependencies. A sensitivity group median does not represent a single plant configuration.</p></details>
   <details><summary>Compare saved studies</summary><label>Comparison study<select value={comparison} onChange={e=>setComparison(e.target.value)}><option value="">Select study</option>{jobs.filter(j=>j.id!==job.id&&j.summary).map(j=><option key={j.id} value={j.id}>{j.settings.label}</option>)}</select></label>{other&&<p>Current median NPV: {format(object(metrics.npv).p50)} · comparison: {format(object(object(other).metrics).npv&&object(object(object(other).metrics).npv).p50)}. Compare scope and price basis before interpreting differences.</p>}</details>
  </section>}
  {!drawerOpen&&error&&<p className="error" role="alert">{error}</p>}
  <AnalysisDrawer open={drawerOpen} title={sensitivity?`Sensitivity · ${sensitivity.label}`:drawerView==='configuration'?`Variation ${Number(representative?.index??inspecting??0)+1}`:'Explore variations'} onClose={closeDrawer}>
   {sensitivity&&<section className="mc-card"><small>Low/high groups summarize multiple configurations. Below is an actual contributing variation.</small><div className="toolbar">{[['Low input group',sensitivity.low_runs],['High input group',sensitivity.high_runs],...rows(sensitivity.groups).map(g=>[String(g.configuration),g.runs])].map(([name,indices])=>Array.isArray(indices)&&indices.length>0?<button className="secondary" key={String(name)} onClick={()=>{setGroupIndices(indices.map(Number));void inspect(Number(indices[0]));}}>{String(name)} · {indices.length}</button>:null)}<button className="secondary" onClick={()=>{request.current++;setInspecting(null);setRepresentative(null);setDrawerView('runs');}}>Browse contributing variations</button></div><details><summary>Full sensitivity setup</summary><p>{String(sensitivity.basis)}</p><pre className="mc-json">{JSON.stringify(job.settings,null,2)}</pre></details></section>}
   {drawerView==='configuration'&&<button type="button" className="secondary" onClick={()=>{request.current++;setInspecting(null);setRepresentative(null);setDrawerView('runs');}}>← Variation list</button>}
   {drawerView==='runs'&&explore}
   {inspecting!==null&&<p className="notice" role="status">Loading variation {inspecting+1} and its frozen configuration…</p>}
   {error&&<p className="error" role="alert">{error}</p>}
   {drawerView==='configuration'&&representative&&<RunConfiguration run={representative} id={id} jobId={job.id}/>}
  </AnalysisDrawer>
 </>;
}
