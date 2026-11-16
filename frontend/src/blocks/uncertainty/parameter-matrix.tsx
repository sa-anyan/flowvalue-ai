'use client';
import {useState} from 'react';
import {AnalysisDrawer} from './analysis-drawer';
import type {Parameter} from '@/lib/monte-carlo';
import {canSample,variationCategories,variationGroup} from './variation-scope';
import './variation-scope.css';

export function ConfigurationChoices({parameter:p,disabled,onChange}:{parameter:Parameter;disabled:boolean;onChange:(patch:Partial<Parameter>)=>void}) {
 const choices=Object.keys(p.choice_labels||{}).length?Object.keys(p.choice_labels!):p.choices.map(String);
 return <fieldset disabled={disabled}><legend>Exact equipment configurations</legend>
  {choices.map(id=>{const index=p.choices.indexOf(id);return <div className="mc-config-choice" key={id}>
   <label><input type="checkbox" checked={index>=0} onChange={e=>{const next=e.target.checked?[...p.choices,id]:p.choices.filter(c=>c!==id);onChange({choices:next,probabilities:next.map(()=>1/next.length)});}}/>{p.choice_labels?.[id]||id} <small>{id}</small></label>
   <button type="button" className="secondary" onClick={()=>onChange({choices:[id],probabilities:[1],enabled:true})}>Use only this</button>
   {index>=0&&<label>Weight<input aria-label={`Probability weight for ${id}`} type="number" step="any" min="0" max="1" value={p.probabilities[index]??''} onChange={e=>onChange({probabilities:p.probabilities.map((v,i)=>i===index?Number(e.target.value):v)})}/></label>}
  </div>;})}
  <small>A single choice fixes that configuration. Multiple choices use the weights shown, which must sum to 1. Selecting choices starts with equal weights; these are analyst assumptions, not validated likelihoods. Alternative models still require compatible sizing and scope.</small>
 </fieldset>;
}

function ParameterEditor({p,disabled,onChange}:{p:Parameter;disabled:boolean;onChange:(patch:Partial<Parameter>)=>void}) {
 const [error,setError]=useState('');
 function numericList(field:'choices'|'probabilities',input:string){const values=input.split(',').map(s=>s.trim()).filter(Boolean).map(Number);if(!values.length||values.some(n=>!Number.isFinite(n))){setError('Enter finite numbers separated by commas.');onChange({[field]:[]});return;}setError('');onChange({[field]:values});}
 return <><p>Baseline: <strong>{String(p.baseline??p.mode??'Not supplied')}</strong> {p.unit}</p><label className="check"><input type="checkbox" checked={p.enabled} disabled={disabled||Boolean(p.review_required)} onChange={e=>onChange({enabled:e.target.checked})}/>Vary this input</label>
 {p.review_required&&<p className="notice">{p.review_required}</p>}
 {p.kind==='configuration'?<ConfigurationChoices parameter={p} disabled={disabled} onChange={onChange}/>:<><label>Distribution<select aria-label={`Distribution for ${p.label}`} disabled={disabled} value={p.distribution} onChange={e=>onChange({distribution:e.target.value})}>{['triangular','uniform','normal','lognormal','discrete'].map(d=><option key={d}>{d}</option>)}</select></label>
 {p.distribution==='discrete'?<div className="mc-control-grid"><label>Values, separated by commas<input defaultValue={p.choices.join(', ')} onBlur={e=>numericList('choices',e.target.value)} disabled={disabled}/></label><label>Weights, separated by commas<input defaultValue={p.probabilities.join(', ')} onBlur={e=>numericList('probabilities',e.target.value)} disabled={disabled}/></label></div>:<div className="mc-matrix-range">{(['minimum','mode','maximum'] as const).filter(k=>p.distribution!=='uniform'||k!=='mode').map(k=><label key={k}>{k==='mode'?p.distribution==='normal'?'Mean':p.distribution==='lognormal'?'Median':'Most likely':k==='minimum'?'Low':'High'}<input aria-label={`${p.label} ${k}`} disabled={disabled} type="number" step="any" value={p[k]??''} onChange={e=>onChange({[k]:e.target.value===''?null:Number(e.target.value)})}/></label>)}{['normal','lognormal'].includes(p.distribution)&&<label>{p.distribution==='lognormal'?'Log sigma':'Std deviation'}<input aria-label={`${p.label} standard deviation`} disabled={disabled} type="number" min="0" step="any" value={p.stddev??''} onChange={e=>onChange({stddev:e.target.value===''?null:Number(e.target.value)})}/></label>}</div>}</>}
 {error&&<p role="alert" className="error">{error}</p>}
 <details><summary>Evidence and assumptions</summary><label>Source<input disabled={disabled} value={p.source} onChange={e=>onChange({source:e.target.value})}/></label><label>Range rationale<textarea disabled={disabled} value={p.rationale} onChange={e=>onChange({rationale:e.target.value})}/></label><p>{p.uncertainty}</p><p>{p.confidence}</p></details>
 <details><summary>Exact calculation targets</summary>{p.targets.map(t=><p className="mc-config-values" key={t.join('.')}>{t.join(' › ')}</p>)}</details>
 <p role="status">{p.enabled?(canSample(p)?'Selected · range and weights ready for validation':'Selected · review range, source or weights before running'):'Held fixed at baseline'}</p>
 </>;
}
export function ParameterMatrix({parameters,disabled,onChange}:{parameters:Parameter[];disabled:boolean;onChange:(id:string,patch:Partial<Parameter>)=>void}) {
 const [selected,setSelected]=useState(''),[query,setQuery]=useState('');
 const current=parameters.find(p=>p.id===selected);
 const filtered=parameters.filter(p=>!query||`${p.label} ${p.unit}`.toLowerCase().includes(query.toLowerCase()));
 const description=(p:Parameter)=>p.kind==='configuration'?`${p.choices.length} selected configuration${p.choices.length===1?'':'s'}`:p.minimum!==null&&p.maximum!==null?`${p.minimum}–${p.maximum} · ${p.distribution}`:'Range needed';
 return <section className="mc-card" aria-label="Select variations from equipment to revenue"><div className="mc-card-head"><div><h2>Select inputs to vary</h2><small>{parameters.filter(p=>p.enabled).length} selected · 200 variations · other inputs stay fixed</small></div><input type="search" aria-label="Find sampling input" placeholder="Find an input…" value={query} onChange={e=>setQuery(e.target.value)}/></div>
 <p className="muted">Expand a category. Click an input to edit its exact configuration or range.</p>
 <div className="mc-selection-list">{variationCategories.map(category=>{const items=filtered.filter(p=>variationGroup(p)[0]===category);return items.length?<details key={category} open={query?true:undefined}><summary>{category} · {items.filter(p=>p.enabled).length} selected / {items.length} inputs</summary><div className="mc-matrix-scroll"><table className="mc-matrix"><thead><tr><th>Vary</th><th>Input</th><th>Baseline</th><th>Range / configuration</th></tr></thead><tbody>{items.map(p=><tr key={p.id}><td><input aria-label={`Vary ${p.label}`} type="checkbox" disabled={disabled||Boolean(p.review_required)} checked={p.enabled} onChange={e=>onChange(p.id,{enabled:e.target.checked})}/></td><th scope="row"><button type="button" className="mc-input-inspect" aria-label={`Edit ${p.label}`} title={`${p.source}. ${p.rationale}. Click to inspect and edit.`} onClick={()=>setSelected(p.id)}>{p.label}</button><small>{p.unit}{p.enabled&&!canSample(p)?' · review needed':''}</small></th><td>{String(p.baseline??p.mode??'Not supplied')}</td><td>{description(p)}</td></tr>)}</tbody></table></div></details>:null;})}</div>
 <AnalysisDrawer open={Boolean(current)} title={current?.label||'Sampling input'} onClose={()=>setSelected('')}>{current&&<ParameterEditor key={current.id} p={current} disabled={disabled} onChange={patch=>onChange(current.id,patch)}/>}</AnalysisDrawer>
 </section>;
}
