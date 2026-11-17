'use client';

import {withCurrency} from '@/lib/display-currency';
import {useId, useMemo, useState} from 'react';
import {list, obj, text, type Row} from '@/lib/guided-flow';
import {analystCsv, analystNumber, capexCostTree, costReconciliation, equipmentCostTree, exactMoney, opexCostTree, paretoRows, revenueCostTree, treemapRects, type CostNode} from '@/lib/analyst-costs';
import './analyst-cost-explorer.css';
import {SourceDocumentLink} from './evidence-note';

const palette=['#176779','#268374','#8a6b2a','#6f65a7','#537b9e','#a05c53','#69824c','#a06a87'];
const label=(value:string)=>value.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
const compact=(value:unknown)=>analystNumber(value)===null?'Pending':new Intl.NumberFormat('en-GB',{notation:'compact',maximumFractionDigits:2}).format(analystNumber(value)!);
const tileLabel=(name:string)=>name
 .replace(/\s*\([^)]*\)/g,'')
 .replace(/^pre-costed unit capital.*$/i,'Unit capital')
 .replace(/^yard,? utilities and off.*$/i,'Offsites & utilities')
 .replace(/^start-up and commission.*$/i,'Start-up')
 .replace(/^engineering and supervis.*$/i,'Engineering')
 .replace(/^instrumentation and control.*$/i,'Controls')
 .replace(/^environmental controls.*$/i,'Environment')
 .replace(/^civil \/ structural.*$/i,'Civil works')
 .replace(/^equipment installation.*$/i,'Installation');
const findNode=(root:CostNode,id:string):CostNode|undefined=>root.id===id?root:root.children.map(n=>findNode(n,id)).find(Boolean);

function RecordFields({record,depth=0}:{record:Row;depth?:number}) {
 return <dl className="aci-fields">{Object.entries(record).map(([key,value])=><div key={key}><dt>{label(key)}</dt><dd>{value===null||value===undefined||value===''?'Not established':typeof value==='object'?<><SourceDocumentLink source={value}/><details><summary>{Array.isArray(value)?`${value.length} saved records`:'Inspect saved fields'}</summary>{depth<3?<RecordFields record={obj(Array.isArray(value)?Object.fromEntries(value.map((v,i)=>[String(i+1),v])):value)} depth={depth+1}/>:<pre>{JSON.stringify(value,null,2)}</pre>}</details></>:typeof value==='string'&&/^https?:\/\/[^\s]+$/.test(value)?<a href={value} target="_blank" rel="noreferrer">Open source ↗</a>:String(value)}</dd></div>)}</dl>;
}

/** Labels follow each tile's rendered pixel size, rather than its percentage area. */
function CompositionTreemap({tiles,currency,share,color,dimmed,onChoose}:{tiles:ReturnType<typeof treemapRects>;currency:string;share:(n:CostNode)=>string;color:(n:CostNode)=>string;dimmed:(n:CostNode)=>boolean;onChoose:(n:CostNode)=>void}) {
 const [activeId,setActiveId]=useState('');
 const active=tiles.find(t=>t.node.id===activeId)?.node;
 return <>
  <div className="aci-treemap" aria-label="Cost composition treemap" onPointerLeave={()=>setActiveId('')}>
   {tiles.map(({node,x,y,width,height})=><button key={node.id} className="aci-tile" style={{left:x+'%',top:y+'%',width:width+'%',height:height+'%',background:color(node),opacity:dimmed(node)?.2:1}}
    title={`${node.label}: ${withCurrency(exactMoney(node.amount),currency)} ${currency}; ${share(node)}`} aria-label={`${node.label}: ${withCurrency(exactMoney(node.amount),currency)} ${currency}, ${share(node)}. ${node.children.length?'Drill into records':'Inspect evidence'}`}
    onPointerEnter={()=>setActiveId(node.id)} onFocus={()=>setActiveId(node.id)} onBlur={()=>setActiveId('')} onClick={()=>onChoose(node)}>
    <span className="aci-tile-content" aria-hidden="true"><span className="aci-tile-name">{tileLabel(node.label)}</span><strong>{withCurrency(compact(node.amount),currency)}</strong><small>{share(node)}</small></span>
   </button>)}
  </div>
  <div className="aci-map-readout" role="status" aria-live="polite" aria-atomic="true">{active?<><b>{active.label}</b><span>{exactMoney(active.amount)} {currency} · {share(active)} of known positive costs</span></>:<><b>Explore any tile</b><span>Hover or focus for its full name and exact value. Small tiles stay proportional; every record is also in Ranked drivers and Exact ledger.</span></>}</div>
 </>;
}

export function AnalystCostExplorer({root,currency,period,revision,stale=false,context,assessmentId=''}:{root:CostNode;currency:string;period:string;revision:string;stale?:boolean;context?:string;assessmentId?:string}) {
 const id=useId();
 const [path,setPath]=useState<string[]>([]),[view,setView]=useState<'composition'|'pareto'|'waterfall'|'ledger'>('composition'),[query,setQuery]=useState(''),[selectedId,setSelectedId]=useState('');
 const trail=[root];
 for(const key of path){const next=trail.at(-1)!.children.find(n=>n.id===key);if(!next)break;trail.push(next);}
 const current=trail.at(-1)!;
 const report=costReconciliation(current);
 const nodes=current.children;
 const visible=nodes.filter(n=>!query||`${n.label} ${JSON.stringify(n.record)}`.toLowerCase().includes(query.toLowerCase()));
 const sorted=visible.slice().sort((a,b)=>analystNumber(a.amount)===null?analystNumber(b.amount)===null?0:1:analystNumber(b.amount)===null?-1:Math.abs(analystNumber(b.amount)!)-Math.abs(analystNumber(a.amount)!));
 const signed=nodes.some(n=>(analystNumber(n.amount)??0)<0);
 const known=nodes.filter(n=>analystNumber(n.amount)!==null);
 const pareto=paretoRows(nodes);
 const tiles=treemapRects(nodes, 1.6);
 const selected=selectedId?findNode(root,selectedId):undefined;
 const peak=Math.max(1,...nodes.map(n=>Math.abs(analystNumber(n.amount)??0)));
 const totalPositive=known.reduce((sum,n)=>sum+Math.max(0,analystNumber(n.amount)!),0);
 const share=(node:CostNode)=>signed||!totalPositive||analystNumber(node.amount)===null?'—':`${(analystNumber(node.amount)!/totalPositive*100).toFixed(1)}%`;
 const color=(node:CostNode)=>palette[Math.max(0,nodes.indexOf(node))%palette.length];
 const choose=(node:CostNode)=>{if(node.children.length){setPath([...trail.slice(1).map(n=>n.id),node.id]);setQuery('');setSelectedId('');}else setSelectedId(node.id);};
 function download(){const blob=new Blob(['\ufeff'+analystCsv(root,currency,period,revision,assessmentId)],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='FlowValue-analyst-chart-records.csv';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);}
 let cumulative=0;
 const waterfall=nodes.filter(n=>analystNumber(n.amount)!==null).map(node=>{const start=cumulative;cumulative+=analystNumber(node.amount)!;return {node,start,end:cumulative};});
 const low=Math.min(0,...waterfall.flatMap(r=>[r.start,r.end]),report.expected??0),high=Math.max(1,...waterfall.flatMap(r=>[r.start,r.end]),report.expected??0);
 const x=(value:number)=>200+(value-low)/(high-low)*460;
 const waterfallHeight=60+waterfall.length*36;
 return <section id="analyst-cost-workbench" className="aci" aria-labelledby={id}>
  <div className="aci-heading"><div><span className="aci-eyebrow">ANALYST WORKBENCH / COST LINEAGE</span><h2 id={id}>What drives every part of the total?</h2><p>{context||root.grain}</p></div><button className="gf-secondary" onClick={download}>Download full lineage CSV ↓</button></div>
  <div className="aci-basis"><span>{currency||'Currency not established'} · {period||'Period not established'}</span><span>Revision {revision||'not established'}{stale?' · Inputs changed; saved figures shown':''}</span></div>
  <nav className="aci-breadcrumb" aria-label="Cost decomposition path">{trail.map((node,index)=><button key={node.id} aria-current={index===trail.length-1?'location':undefined} onClick={()=>{setPath(trail.slice(1,index+1).map(n=>n.id));setSelectedId('');setQuery('');}}>{index>0&&<span aria-hidden="true">› </span>}{node.label}</button>)}</nav>
  <details className="aci-reconciliation"><summary>Reconciliation &amp; coverage · {known.length} / {nodes.length} amounts known · {report.matches ? 'matches saved parent' : 'review difference'}</summary>
  <div className="aci-stats"><div><small>Saved / parent amount</small><strong>{withCurrency(exactMoney(current.amount),currency)}</strong></div><div><small>Known child records</small><strong>{known.length?withCurrency(exactMoney(report.known),currency):'Not established'}</strong></div><div><small>Coverage at this level</small><strong>{known.length} <span>/ {nodes.length} amounts known</span></strong></div><div data-review={!report.complete}><small>{report.matches?'Reconciles to parent':'Unallocated difference'}</small><strong>{report.delta===null?'Not established':withCurrency(exactMoney(report.delta),currency)}</strong></div></div>
  <div className="aci-accounting" role="note">{!nodes.length?'No additive child records were supplied at this level; no itemisation is inferred.':report.complete?'Known child amounts reconcile to this saved parent within one cent.':report.expected===null?'A complete parent total is unavailable. Only known records are shown.':report.matches?'Known amounts reconcile, but unresolved scope remains.':'Child records do not fully reconcile to the saved parent. The difference is shown, never allocated to invented items.'} {report.unresolved>0&&`${report.unresolved} ${report.unresolved===1?'record has an unresolved amount':'records have unresolved amounts'}.`} Group subtotals are chart summaries of saved lines; they do not recalculate the economic model.</div>
  </details>
  <div className="aci-toolbar"><div className="aci-switch" role="group" aria-label="Analyst chart view">{(['composition','pareto','waterfall','ledger'] as const).map(key=><button key={key} aria-pressed={view===key} onClick={()=>setView(key)}>{key==='composition'?'Composition':key==='pareto'?'Pareto / concentration':key==='waterfall'?'Contribution waterfall':'Exact ledger'}</button>)}</div><label><span className="gf-sr-only">Search analyst cost records</span><input type="search" placeholder="Find a cost, formula or source…" value={query} onChange={e=>setQuery(e.target.value)}/></label></div>
  {query&&<p className="aci-filter-note">{visible.length} matching records. Chart areas and percentages retain the full current-level denominator. <button className="gf-link" onClick={()=>setQuery('')}>Clear filter</button></p>}
  {view==='composition'&&<div className="aci-chart-grid"><article><h3>Composition map</h3><p>Area = known positive amount. Select a category to drill into its saved records.</p>{!signed&&tiles.length?<CompositionTreemap tiles={tiles} currency={currency} share={share} color={color} dimmed={node=>Boolean(query&&!visible.includes(node))} onChoose={choose}/>:<div className="aci-empty">{signed?'Signed costs cannot be represented as areas. Use the ranked drivers, waterfall or ledger.':'No positive known amounts to map. Zero and unresolved values remain in the ledger.'}</div>}<details className="aci-help"><summary>How to read this chart</summary><p>Area represents known positive amounts at this level, not the completeness of the estimate. Zero, missing values and combined references are not assigned an area. Colours identify sibling records, not confidence. Search dims unmatched areas without changing the total.</p></details></article><article><h3>Ranked drivers</h3><p>All records, including zero and unresolved amounts. Parent and children are separate views.</p><div className="aci-drivers">{sorted.map(node=><button key={node.id} className="aci-driver" onClick={()=>choose(node)}><span><b>{node.label}</b><strong title={withCurrency(exactMoney(node.amount),currency)}>{withCurrency(compact(node.amount),currency)}</strong><small>{share(node)}</small></span><span className="aci-track"><i style={{width:(analystNumber(node.amount)===null?0:Math.abs(analystNumber(node.amount)!)/peak*100)+'%',background:color(node)}}/></span><small>{node.children.length?`${node.children.length} ${node.children.length===1?'record':'records'} · drill down →`:node.grain+' · inspect →'}</small></button>)}{!visible.length&&<p className="aci-empty">No records match this selection.</p>}</div></article></div>}
  {view==='pareto'&&<article className="aci-wide-chart"><h3>Which drivers account for most of this scope?</h3><p>Cumulative share of all known non-negative amounts at this level. The 80% line is a reading guide, not a prediction or confidence score.</p>{pareto&&pareto.some(r=>r.share!==null)?<><div className="aci-svg-scroll"><svg viewBox={`0 0 760 ${Math.max(250,pareto.length*34+70)}`} role="group" aria-label="Pareto chart with cumulative share of known costs"><line x1="500" x2="500" y1="35" y2={pareto.length*34+35} className="aci-guide"/><text x="500" y="19" textAnchor="middle">80% cumulative</text>{pareto.map(({node,share:cumulativeShare},i)=><g key={node.id} opacity={query&&!visible.includes(node)?.2:1}><text x="0" y={58+i*34}>{node.label.length>26?node.label.slice(0,25)+'…':node.label}</text><rect tabIndex={0} role="button" aria-label={`${node.label}: ${withCurrency(exactMoney(node.amount),currency)} ${currency}. Inspect cost driver`} onClick={()=>choose(node)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(node);}}} x="200" y={42+i*34} width={analystNumber(node.amount)!/peak*375} height="19" fill={color(node)}><title>{`${node.label}: ${withCurrency(exactMoney(node.amount),currency)} ${currency}`}</title></rect><circle cx={200+(cumulativeShare??0)*375} cy={51+i*34} r="5" fill="var(--gf-ink)"/><text x="610" y={57+i*34}>{withCurrency(exactMoney(node.amount),currency)}</text><text x="748" textAnchor="end" y={57+i*34}>{cumulativeShare===null?'—':(cumulativeShare*100).toFixed(1)+'%'}</text></g>)}</svg></div><div className="aci-legend">Bars: amount · Dots: cumulative share · {report.unresolved} unresolved amounts excluded from the denominator.</div></>:<div className="aci-empty">Concentration percentages are unavailable for signed adjustments or a zero known total. Use the waterfall or exact ledger.</div>}</article>}
  {view==='waterfall'&&<article className="aci-wide-chart"><h3>How the known contributions build up</h3><p>Contributions start from zero. This is a cost build-up, not a cash-flow timeline. Unresolved amounts do not receive a bar.</p>{waterfall.length?<div className="aci-svg-scroll"><svg viewBox={`0 0 760 ${waterfallHeight}`} role="group" aria-label="Contribution waterfall of known saved amounts">{report.expected!==null&&<><line x1={x(report.expected)} x2={x(report.expected)} y1="30" y2={waterfallHeight-10} className="aci-guide"/><text x={x(report.expected)} y="18" textAnchor="middle">Saved parent</text></>}{waterfall.map(({node,start,end},i)=><g key={node.id} opacity={query&&!visible.includes(node)?.2:1}><text x="0" y={54+i*36}>{node.label.length>26?node.label.slice(0,25)+'…':node.label}</text><line x1={x(start)} x2={x(start)} y1={30+i*36} y2={58+i*36} stroke="var(--gf-line)"/><rect tabIndex={0} role="button" aria-label={`${node.label}: ${withCurrency(exactMoney(node.amount),currency)} ${currency}. Inspect contribution`} onClick={()=>choose(node)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(node);}}} x={x(Math.min(start,end))} y={37+i*36} width={Math.abs(x(end)-x(start))} height="20" fill={end<start?'var(--gf-neg)':color(node)}><title>{`${node.label}: ${withCurrency(exactMoney(node.amount),currency)}; cumulative ${exactMoney(end)}`}</title></rect><text x="750" textAnchor="end" y={54+i*36}>{withCurrency(exactMoney(node.amount),currency)}</text></g>)}</svg></div>:<p className="aci-empty">No known contributions available.</p>}<div className="aci-legend">Known build-up: {known.length?exactMoney(report.known):'not established'} {currency} · Difference to saved parent: {report.delta===null?'not established':exactMoney(report.delta)}.</div></article>}
  {view==='ledger'&&<div className="aci-ledger-scroll"><table><caption>{current.label} · {currency||'currency not established'} · {period||'period not established'}</caption><thead><tr><th>Saved driver</th><th>Exact amount</th><th>Known share</th><th>Detail available</th><th>Evidence</th></tr></thead><tbody>{sorted.map(node=><tr key={node.id}><th scope="row"><button className="gf-link" onClick={()=>choose(node)}>{node.label}{node.children.length?' →':''}</button></th><td>{withCurrency(exactMoney(node.amount),currency)}</td><td>{share(node)}</td><td>{node.grain}</td><td><button className="gf-secondary" onClick={()=>setSelectedId(node.id)}>Inspect record</button></td></tr>)}</tbody></table>{!visible.length&&<p className="aci-empty">No matching records.</p>}</div>}
  {selected&&<div className="aci-inspector" role="region" aria-label="Saved calculation record"><div className="aci-heading"><div><span className="aci-eyebrow">SAVED RECORD / SOURCE LINEAGE</span><h3>{selected.label}</h3></div><button className="gf-secondary" onClick={()=>setSelectedId('')}>Close record ×</button></div><strong className="aci-inspector-value">{withCurrency(exactMoney(selected.amount),currency)} <small>{currency} · {period}</small></strong><p className="aci-granularity">{selected.grain}</p><RecordFields record={selected.record}/></div>}
  <details className="aci-help"><summary>Scope, granularity and reconciliation evidence</summary><p>A factor-based piping or installation allowance does not specify the number of bolts, valves or labour hours. Item-level precision requires a supplied, reviewed bill of materials or quantity take-off. This workbench follows the saved calculation as far as it goes and shows gaps rather than manufacturing that detail.</p><RecordFields record={current.record}/></details>
 </section>;
}

export function CapexDriverAnalysis({result,equipment,revision,stale,assessmentId}:{result:Row;equipment:Row[];revision:string;stale?:boolean;assessmentId?:string}) {
 const root=useMemo(()=>capexCostTree(result,equipment),[result,equipment]);
 return <AnalystCostExplorer root={root} assessmentId={assessmentId} currency={text(result.currency)} period={text(result.period)} revision={revision} stale={stale} context="Investment → cost category → factor or equipment → saved calculation and evidence. Embedded and combined scope is counted only once."/>;
}
export function OpexDriverAnalysis({result,revision,stale,assessmentId}:{result:Row;revision:string;stale?:boolean;assessmentId?:string}) {
 const [year,setYear]=useState(''),[grouping,setGrouping]=useState<'category'|'behavior'|'method'>('category');
 const years=Object.keys(obj(result.years)).sort((a,b)=>Number(a)-Number(b));
 const currentYear=years.includes(year)?year:years[0]||'';
 const root=useMemo(()=>opexCostTree(result,currentYear,grouping),[result,currentYear,grouping]);
 return <div className="aci-domain"><div className="aci-domain-controls"><label>Analyst operating year<select aria-label="Analyst operating year" value={currentYear} disabled={!years.length} onChange={e=>setYear(e.target.value)}>{!years.length&&<option value="">Not calculated</option>}{years.map(y=><option key={y} value={y}>Year {y}</option>)}</select></label><label>Decompose by<select aria-label="OPEX decomposition" value={grouping} onChange={e=>setGrouping(e.target.value as typeof grouping)}><option value="category">Cost category</option><option value="behavior">Fixed / variable behavior</option><option value="method">Calculation method</option></select></label></div><AnalystCostExplorer key={root.id} root={root} assessmentId={assessmentId} currency={text(result.currency)} period={text(result.price_period)} revision={revision} stale={stale} context="Selected-year cash costs → category or behavior → individual ledger line → quantity, rate, method and source. Non-cash and financing entries remain outside cash OPEX."/></div>;
}
export function RevenueDriverAnalysis({result,config,revision,draft=false,assessmentId}:{result:Row;config:Row;revision:string;draft?:boolean;assessmentId?:string}) {
 const root=useMemo(()=>revenueCostTree(result,config,draft),[result,config,draft]);
 return <AnalystCostExplorer key={root.id} root={root} assessmentId={assessmentId} currency={text(obj(result.basis).currency)} period={text(obj(result.basis).price_period)} revision={revision} context={draft?'Unapproved draft income · values from the deterministic preview.':'100% scheduled-operation income → income category → commercial line → saved quantities, terms, price assumptions and source. Avoided OPEX is separate.'}/>;
}

export function EquipmentDriverAnalysis({result,revision,assessmentId}:{result:Row;revision:string;assessmentId?:string}) {
 const [selected,setSelected]=useState('');
 const bases=list(obj(result.priced_summary).amounts);
 const key=(r:Row)=>`${text(r.currency)}:${text(r.period)}`;
 const basis=bases.find(r=>key(r)===selected)||bases[0]||{};
 const root=useMemo(()=>equipmentCostTree(result,basis),[result,basis]);
 return <div className="aci-domain">{bases.length>1&&<div className="aci-domain-controls"><label>Equipment monetary basis<select aria-label="Equipment monetary basis" value={key(basis)} onChange={e=>setSelected(e.target.value)}>{bases.map(r=><option key={key(r)} value={key(r)}>{text(r.currency)} · {text(r.period)}</option>)}</select></label></div>}<AnalystCostExplorer key={root.id} root={root} assessmentId={assessmentId} currency={text(basis.currency)} period={text(basis.period)} revision={revision} context="Saved equipment cost → monetary basis and source scope → asset → sizing inputs, source correlation and escalation. Package costs are not decomposed into invented parts."/></div>;
}
