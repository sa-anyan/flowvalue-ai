'use client';
import {useState,type ReactNode} from 'react';
import './revenue-dashboard.css';
import {RevenueComparison} from './revenue-comparison';
import {streamColour,revenueSeries} from './revenue-series';

type Row=Record<string,unknown>;
const obj=(v:unknown):Row=>v&&typeof v==='object'&&!Array.isArray(v)?v as Row:{};
const rows=(v:unknown):Row[]=>Array.isArray(v)?v.map(obj):[];
const number=(v:unknown):number|null=>v===null||v===undefined||v===''||!Number.isFinite(Number(v))?null:Number(v);
const fmt=(v:unknown)=>number(v)===null?'—':new Intl.NumberFormat('en-GB',{maximumFractionDigits:2}).format(Number(v));
const names:Record<string,string>={product_sales:'Product sales',processing_services:'Processing services',capacity_availability:'Capacity',infrastructure_usage:'Infrastructure',environmental_attributes:'Environmental',other_contractual_income:'Contract income',avoided_cost:'Cost savings'};

export function RevenueDashboard({config,result,questions,approved,busy,dirty,drawer}: {
 config:unknown;result:unknown;questions:string[];approved:boolean;busy:boolean;dirty:boolean;
 drawer:ReactNode;
}) {
 const [year,setYear]=useState(''),[selected,setSelected]=useState(''),[query,setQuery]=useState('');
 const c=obj(config),r=obj(result),annual=rows(r.annual).sort((a,b)=>Number(a.year)-Number(b.year));
 const activeYear=annual.some(a=>String(a.year)===year)?year:String(annual[0]?.year??1);
 const current=annual.find(a=>String(a.year)===activeYear);
 const currency=String(obj(r.basis).currency??obj(c.price_basis).currency??'Currency pending');
 const money=(v:unknown)=>number(v)===null?'—':`${currency} ${fmt(v)}`;
 const products=rows(r.products).filter(p=>String(p.year)===activeYear),commercial=rows(r.commercial).filter(p=>String(p.year)===activeYear);
 const lines=[...rows(c.sales).map(v=>({...v,group:'product_sales',pending:false})),...rows(c.commercial_lines).map(v=>({...v,group:String(v.category),pending:false})),...rows(c.pending_inputs).map(v=>({...v,group:String(v.category),pending:true})),...rows(c.avoided_costs).map(v=>({...v,group:'avoided_cost',pending:false}))] as Row[];
 const detailsFor=(line:Row)=>line.group==='product_sales'?products.find(p=>p.product_id===line.id):line.group==='avoided_cost'?undefined:commercial.find(p=>p.line_id===line.id);
 const income=(line:Row)=>{const d=detailsFor(line);return line.pending||line.group==='avoided_cost'?null:number(d?.net_sales_revenue??d?.revenue);};
 const filtered=lines.filter(l=>`${l.name} ${l.group} ${l.context_quote}`.toLowerCase().includes(query.toLowerCase()));
 const chosen=filtered.find(l=>String(l.id)===selected)||filtered[0],detail=chosen?detailsFor(chosen):undefined;
 const palette=new Map(revenueSeries(c,r).streams.map(s=>[s.id,s.colour]));
 const colourFor=(l:Row)=>{const id=(l.group==='product_sales'?'product:':'commercial:')+String(l.id);return palette.get(id)??streamColour(id);};
 const openReview=()=>window.dispatchEvent(new CustomEvent('flowvalue:revenue-workspace',{detail:'Revenue Box'}));
 return <section className="rv-dashboard" aria-label="Revenue analyst dashboard">
  <div className="rv-heading"><div><span className="rv-eyebrow">COMMERCIAL OVERVIEW</span><h2>Revenue overview<span className="rv-live">{busy?'Processing':approved?'Approved':'Draft review'}</span></h2></div></div>
  <div className="rv-status"><span className="rv-status-dot"/>{dirty?'Unsaved edits · charts show the last saved calculation':busy?'Processing your assessment…':current?'Saved Python calculation':'Awaiting approved calculation · extracted assumptions below'}<button onClick={openReview}>{questions.length?`${questions.length} review items →`:'Review assumptions →'}</button></div>
  <div className="rv-kpis rv-kpis-clean"><article><span>ANNUAL REVENUE</span><strong>{money(current?.sales_revenue)}</strong><small>Operating year {activeYear} · {approved?'approved basis':'draft / review required'}</small></article><article><span>INCOME STREAMS</span><strong>{lines.filter(l=>!l.pending&&l.group!=='avoided_cost').length}</strong><small>{new Set(lines.filter(l=>!l.pending&&l.group!=='avoided_cost').map(l=>l.group)).size} MECE categories · {lines.filter(l=>l.pending).length} pending</small></article><article><span>MODEL HORIZON</span><strong>{annual.length||Number(obj(c.financial).operating_years)||'—'}<em> years</em></strong><small>{currency} · undiscounted revenue</small></article></div>
  <div className="rv-navigation"><div className="rv-overview-actions"><span className="rv-overview-label">Overview</span>{drawer}</div>{annual.length>0&&<label>Operating year <select aria-label="Dashboard operating year" value={activeYear} onChange={e=>setYear(e.target.value)}>{annual.map(a=><option key={String(a.year)} value={String(a.year)}>Year {String(a.year)}</option>)}</select></label>}</div>
  <RevenueComparison config={c} result={r} year={activeYear} onYear={setYear} currency={currency} onReview={openReview}/>
   <details className="rv-panel rv-streams"><summary className="rv-extracted-summary"><span>Extracted revenue <span className="rv-counter">{lines.length} lines</span></span><small>Expand to inspect methods, quantities &amp; evidence</small></summary><div className="rv-panel-title"><p>Select a card to inspect its quantity, price and source evidence.</p><input aria-label="Search revenue streams" type="search" placeholder="Search streams or methods…" value={query} onChange={e=>setQuery(e.target.value)}/></div><div className="rv-stream-layout"><div className="rv-stream-list">{filtered.map((l,i)=><button key={String(l.id)+i} className="rv-stream-card" aria-pressed={chosen===l} onClick={()=>setSelected(String(l.id))}><span className="rv-stream-icon" style={{background:colourFor(l)+'22',color:colourFor(l)}}>{String(l.name??'R').slice(0,1).toUpperCase()}</span><span><strong>{String(l.name??l.id)}</strong><small>{names[String(l.group)]??String(l.group)} · {l.pending?'Pending inputs':l.group==='avoided_cost'?'Separate OPEX adjustment':'Extracted method'}</small><span className="rv-card-peek">{l.context_quote?String(l.context_quote):String(l.rationale??'Select to inspect inputs')}</span></span><b>{l.pending?'Pending':l.group==='avoided_cost'?'OPEX':money(income(l))}<small>Inspect ↗</small></b></button>)}{!filtered.length&&<div className="rv-empty">{lines.length?'No matching streams.':'No extracted methods yet. Add a revenue line or interpret the Revenue Box.'}</div>}</div><div className="rv-inspector" aria-live="polite">{chosen?<><span className="rv-eyebrow">STREAM INSPECTOR</span><h3>{String(chosen.name??chosen.id)}</h3><span className="rv-inspector-type">{names[String(chosen.group)]??String(chosen.group)}</span><div className="rv-inspector-metrics">{[['Annual income',money(income(chosen))],['Quantity sold',detail?.quantity_sold===undefined?'—':`${fmt(detail.quantity_sold)} ${String(detail.quantity_unit??chosen.quantity_unit??'')}`],['Price / rate',`${fmt(detail?.net_selling_price??detail?.rate??chosen.unit_price??rows(chosen.years).find(y=>String(y.year)===activeYear)?.rate??chosen.rate)} / ${String(chosen.quantity_unit??chosen.rate_unit??'unit pending')}`],['Stream mapping',String(chosen.stream_key??'Contract / no stream')]].map(([k,v])=><div key={k}><small>{k}</small><strong>{v}</strong></div>)}</div><details open><summary>Commercial evidence</summary><p>{String(chosen.context_quote??chosen.rationale??chosen.quantity_basis??'No evidence supplied')}</p></details>{detail&&<details><summary>All calculated fields & source references</summary><dl>{Object.entries(detail).map(([key,v])=><div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{typeof v==='object'?JSON.stringify(v):String(v??'—')}</dd></div>)}</dl></details>}{chosen.pending&&<p className="rv-pending">Excluded from income until missing inputs are resolved.</p>}</>:<div className="rv-empty">Select a revenue stream to inspect it here.</div>}</div></div></details>
 </section>;
}
