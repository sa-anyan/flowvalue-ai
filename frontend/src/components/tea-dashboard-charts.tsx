'use client';
import {useState} from 'react';
type Row=Record<string,unknown>;
const obj=(v:unknown):Row=>v&&typeof v==='object'&&!Array.isArray(v)?v as Row:{};
const rows=(v:unknown):Row[]=>Array.isArray(v)?v.map(obj):[];
const num=(v:unknown):number|null=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v))?Number(v):null;
const fmt=(n:number)=>new Intl.NumberFormat('en-GB',{notation:'compact',maximumFractionDigits:2}).format(n);
const colours=['#3578bd','#24a18a','#d39a49','#8069bd','#e07777','#6b93a7','#8ba66a','#cb7ca3'];
type Slice={name:string;value:number};
function Donut({title,eyebrow,slices,onExplore}:{title:string;eyebrow:string;slices:Slice[];onExplore:()=>void}){
 const [selected,setSelected]=useState<number|null>(null);
 const positive=slices.filter(s=>Number.isFinite(s.value)&&s.value>0);
 const total=positive.reduce((a,b)=>a+b.value,0);
 let offset=0;
 const segments=positive.map((s,i)=>{const start=offset;offset+=s.value/total*100;return {s,i,start,end:offset};});
 const gradient=segments.map(v=>`${colours[v.i%colours.length]} ${v.start}% ${v.end}%`).join(', ');
 return <article className="tea-bi-chart"><div className="tea-bi-chart-head"><div><span className="tea-eyebrow">{eyebrow}</span><h3>{title}</h3></div><button type="button" className="tea-bi-explore" onClick={onExplore}>Explore ↗</button></div>
 {positive.length?<><div className="tea-bi-donut-layout"><div className="tea-bi-donut" role="img" aria-label={title+': '+positive.map(s=>s.name+' '+fmt(s.value)).join(', ')} style={{background:`conic-gradient(${gradient})`}}><div className="tea-bi-donut-hole"><small>{selected===null?'Total':positive[selected]?.name}</small><strong>{fmt(selected===null?total:positive[selected]?.value||0)}</strong></div></div><div className="tea-bi-legend">{positive.slice(0,7).map((s,i)=><button type="button" key={s.name+i} aria-pressed={selected===i} onClick={()=>setSelected(selected===i?null:i)}><span className="tea-bi-swatch" style={{background:colours[i%colours.length]}}/><span className="tea-bi-legend-name">{s.name}</span><strong>{Math.round(s.value/total*100)}%</strong></button>)}</div></div><p className="tea-bi-caption">Share of calculated {title.toLowerCase()}. Select a segment label to inspect its value.</p></>:<div className="tea-bi-empty">No reliable cost or revenue breakdown is available yet.</div>}</article>;
}
export function TeaDashboardCharts({stages,onExplore}:{stages:Record<string,{result?:Row}>;onExplore:(key:string)=>void}){
 const [cashMode,setCashMode]=useState<'annual'|'cumulative'>('annual');
 const capex=obj(stages.capex?.result),opex=obj(stages.opex?.result),revenue=obj(stages.revenue?.result),financial=obj(stages.financial?.result);
 const annual=obj(obj(opex.years)['1']);
 const capital=rows(capex.lines).map(r=>({name:String(r.id??r.category??'Capital item').replaceAll('_',' '),value:num(r.amount)||0}));
 const operating=rows(annual.lines).filter(r=>String(r.accounting)==='cash').map(r=>({name:String(r.category??r.id??'Operating item').replaceAll('_',' '),value:num(r.amount)||0}));
 const commercial=[...rows(revenue.products).filter(r=>Number(r.year)===1).map(r=>({name:String(r.product_id??'Product'),value:num(r.net_sales_revenue)||0})),...rows(revenue.commercial).filter(r=>Number(r.year)===1).map(r=>({name:String(r.line_id??'Service'),value:num(r.revenue)||0}))];
 const ledger=rows(financial.ledger).map((r,i)=>({year:num(obj(r.period).year)??i,value:num(cashMode==='annual'?r.fcff:r.cumulative_project_cash)})).filter((r):r is {year:number;value:number}=>r.value!==null);
 const min=Math.min(0,...ledger.map(d=>d.value)),max=Math.max(0,...ledger.map(d=>d.value)),span=max-min||1;
 const points=ledger.map((r,i)=>({x:45+i/Math.max(1,ledger.length-1)*620,y:178-(r.value-min)/span*135,...r}));
 return <section className="tea-bi-dashboard" aria-label="Interactive financial dashboards"><div className="tea-bi-intro"><div><span className="tea-eyebrow">ECONOMIC INTELLIGENCE</span><h2>Inside the project economics</h2><p>Three distinct views of where capital is spent, where annual costs arise and how revenue is generated.</p></div></div><div className="tea-bi-grid">
 <Donut eyebrow="CAPITAL ALLOCATION" title="CAPEX mix" slices={capital} onExplore={()=>onExplore('capex')}/>
 <Donut eyebrow="COST DRIVERS · YEAR 1" title="OPEX mix" slices={operating} onExplore={()=>onExplore('opex')}/>
 <Donut eyebrow="INCOME SOURCES · YEAR 1" title="Revenue mix" slices={commercial} onExplore={()=>onExplore('revenue')}/>
 </div>
 <article className="tea-bi-chart tea-bi-cashflow"><div className="tea-bi-chart-head"><div><span className="tea-eyebrow">INVESTMENT PERFORMANCE</span><h3>Project cash flow</h3></div><div className="tea-bi-chart-actions"><div className="tea-bi-mode"><button aria-pressed={cashMode==='annual'} onClick={()=>setCashMode('annual')}>Annual</button><button aria-pressed={cashMode==='cumulative'} onClick={()=>setCashMode('cumulative')}>Cumulative</button></div><button className="tea-bi-explore" onClick={()=>onExplore('financial')}>Explore ↗</button></div></div>
 {points.length>1?<svg viewBox="0 0 710 215" className="tea-bi-line" role="img" aria-label={cashMode+' project cash flow by year'}><line x1="45" x2="665" y1={178-(0-min)/span*135} y2={178-(0-min)/span*135} stroke="currentColor" opacity=".2"/><polyline fill="none" stroke="#3578bd" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" points={points.map(p=>p.x+','+p.y).join(' ')}/>{points.map((p,i)=><circle key={i} cx={p.x} cy={p.y} r="5" fill="#3578bd"><title>Year {p.year}: {fmt(p.value)}</title></circle>)}<text x="45" y="206" fill="currentColor" fontSize="12">Year {points[0].year}</text><text x="595" y="206" fill="currentColor" fontSize="12">Year {points.at(-1)?.year}</text></svg>:<div className="tea-bi-empty">The saved financial model does not yet contain enough annual cash flow observations.</div>}<p className="tea-bi-caption">Calculated cash flow · switch between annual and cumulative values, then explore the detailed ledger.</p></article>
 </section>;
}
