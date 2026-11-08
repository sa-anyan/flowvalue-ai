'use client';
import {useState} from 'react';
import {revenueSeries} from '@/components/revenue-series';
import {RevenueComparison} from '@/components/revenue-comparison';
import '@/components/revenue-dashboard.css';
type Row=Record<string,unknown>;
const obj=(v:unknown):Row=>v&&typeof v==='object'&&!Array.isArray(v)?v as Row:{};
const rows=(v:unknown):Row[]=>Array.isArray(v)?v.map(obj):[];
const num=(v:unknown):number|null=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v))?Number(v):null;
const fmt=(n:number)=>new Intl.NumberFormat('en-GB',{notation:'compact',maximumFractionDigits:2}).format(n);
const colours=['#3578bd','#24a18a','#d39a49','#8069bd','#e07777','#6b93a7','#8ba66a','#cb7ca3'];
type Slice={name:string;value:number};
function RankedBars({title,slices,currency,basis,onExplore,details,hint='Select a cost driver to inspect its basis'}:{title:string;slices:Slice[];currency:string;basis:string;onExplore:()=>void;details:(name:string)=>Row[];hint?:string}){
 const [selected,setSelected]=useState<string|null>(null);
 const ranked=slices.filter(s=>Number.isFinite(s.value)).sort((a,b)=>b.value-a.value);
 const total=ranked.reduce((sum,s)=>sum+s.value,0),maximum=Math.max(1,...ranked.map(s=>Math.abs(s.value)));
 const active=ranked.find(s=>s.name===selected);
 const share=(value:number)=>total>0?new Intl.NumberFormat('en-GB',{style:'percent',maximumFractionDigits:1}).format(value/total):'Share unavailable';
 return <article className="tea-bi-chart ranked-cost-chart"><div className="tea-bi-chart-head"><h3>{title}</h3><button className="tea-bi-explore" onClick={onExplore}>Explore ↗</button></div><div className="ranked-cost-basis">{currency} · {basis}<span>{title==='Income contribution'?'Revenue':'Cost'} / share</span></div><p className="chart-interaction-hint">{hint} <span aria-hidden="true">↘</span></p>{ranked.length?<div className="ranked-cost-list">{ranked.map((slice,index)=><button className="ranked-cost-row" key={slice.name+index} aria-expanded={active?.name===slice.name} onClick={()=>setSelected(selected===slice.name?null:slice.name)} title={`${slice.name}: ${slice.value.toLocaleString('en-GB',{maximumFractionDigits:2})} ${currency}`}><span className="ranked-cost-label"><span><i className="cost-rank">{String(index+1).padStart(2,'0')}</i>{slice.name.replaceAll('_',' ')}</span><strong>{fmt(slice.value)}</strong><small>{share(slice.value)}</small></span><span className="ranked-cost-track"><span style={{width:`${Math.abs(slice.value)/maximum*100}%`,background:slice.value<0?'var(--negative)':'var(--section-accent,var(--primary))'}}/></span></button>)}</div>:<p className="tea-bi-empty">{title==='Income contribution'?'No calculated income breakdown is available.':'No calculated cost breakdown is available.'}</p>}{active&&<div className="ranked-cost-detail" aria-live="polite"><div className="ranked-detail-heading"><strong>{active.name.replaceAll('_',' ')}</strong><button className="secondary" aria-label="Close cost detail" onClick={()=>setSelected(null)}>×</button></div><p>{active.value.toLocaleString('en-GB',{maximumFractionDigits:2})} {currency} · {share(active.value)} of listed {title==='Income contribution'?'revenue':'costs'}</p>{details(active.name).map((row,i)=><div className="ranked-detail-record" key={i}>{['equipment_tag','curve_id','category','id','method','product_id','line_id','year','quantity','quantity_sold','quantity_unit','rate','rate_unit','net_selling_price','fixed_payment','net_sales_revenue','revenue','behavior','amount','status','rationale'].filter(k=>row[k]!==null&&row[k]!==undefined&&row[k]!=='').map(k=><div key={k}><small>{k.replaceAll('_',' ')}</small><span>{String(row[k])}</span></div>)}</div>)}</div>}</article>;
}
export function TeaDashboardCharts({stages,revenueConfig,onExplore}:{stages:Record<string,{result?:Row;issues?:string[]}>;revenueConfig?:unknown;onExplore:(key:string)=>void}){
 const [cashMode,setCashMode]=useState<'annual'|'cumulative'>('annual');
 const [cashYear,setCashYear]=useState<number|null>(null);
 const [selectedRevenueYear,setSelectedRevenueYear]=useState('');
 const capex=obj(stages.capex?.result),opex=obj(stages.opex?.result),revenue=obj(stages.revenue?.result),financial=obj(stages.financial?.result);
 const operatingYears=Object.keys(obj(opex.years)).sort((a,b)=>Number(a)-Number(b));
 const lastYear=operatingYears.at(-1)||'1';
 const annual=obj(obj(opex.years)[lastYear]);
 const capital=[{name:'Fixed capital',value:num(capex.fixed_capital)},{name:'Start-up',value:num(capex.startup_expenses)},{name:'Working capital',value:num(capex.working_capital)}].filter((r):r is {name:string;value:number}=>r.value!==null);
 const operating=rows(annual.lines).filter(r=>String(r.accounting)==='cash'&&num(r.amount)!==null).map(r=>({name:String(r.category??r.id??'Operating item').replaceAll('_',' '),value:num(r.amount)!}));
 const {years: revenueYears, streams, total: revenueTotal}=revenueSeries(obj(revenueConfig),revenue);
 const revenueYear=revenueYears.includes(selectedRevenueYear)?selectedRevenueYear:revenueYears.at(-1);
 const revenueIndex=revenueYear===undefined?-1:revenueYears.indexOf(revenueYear);
 const revenueCurrency=String(obj(revenue.basis).currency??'Currency pending');
 const revenueRows=[...rows(revenue.products),...rows(revenue.commercial)].filter(row=>String(row.year)===revenueYear);
 const commercial=streams.flatMap(stream=>{
  const value=stream.values[revenueIndex];
  return value==null?[]:[{name:stream.name,value}];
 });
 const revenueBasis=revenueYear?`Operating year ${revenueYear}`:'Awaiting calculated revenue';
 const equipment=rows(obj(stages.equipment?.result).equipment).map(r=>({name:String(r.equipment_tag??'Equipment'),value:num(r.equipment_cost)})).filter((r):r is Slice=>r.value!==null);
 const currency=String(capex.currency??financial.currency??'Currency pending');
 const basis=String(capex.period??financial.financial_base_year??'Price year pending');
 const money=(v:unknown)=>num(v)===null?'Not available':fmt(num(v)!);
 const opexGroups=new Map<string,number>();for(const item of operating)opexGroups.set(item.name,(opexGroups.get(item.name)||0)+item.value);
 const operatingGrouped=[...opexGroups].map(([name,value])=>({name,value}));
 const summaries=(values:{name:string;value:number|null}[],key:string)=><div className="hero-cost-summary">{values.map(v=><button key={v.name} onClick={()=>onExplore(key)}><span>{v.name}</span><strong>{v.value===null?'Not available':fmt(v.value)}</strong></button>)}</div>;
 const allocation=(slices:Slice[],key:string)=>{const valid=slices.filter(v=>v.value>0),total=valid.reduce((sum,v)=>sum+v.value,0);return <div className="hero-allocation"><div className="allocation-track" aria-label="Cost allocation">{valid.map((v,i)=><button key={v.name+i} style={{width:`${v.value/total*100}%`,background:colours[i%colours.length]}} title={`${v.name}: ${fmt(v.value)}`} aria-label={`${v.name}: ${fmt(v.value)}`} onClick={()=>onExplore(key)}/>)}</div><div className="allocation-labels">{valid.map((v,i)=><span key={v.name+i}><i style={{background:colours[i%colours.length]}}/>{v.name} <strong>{Math.round(v.value/total*100)}%</strong></span>)}</div></div>;};
 const ledger=rows(financial.ledger).map((r,i)=>({year:num(obj(r.period).year)??i,value:num(cashMode==='annual'?r.fcff:r.cumulative_project_cash)})).filter((r):r is {year:number;value:number}=>r.value!==null);
 const min=Math.min(0,...ledger.map(d=>d.value)),max=Math.max(0,...ledger.map(d=>d.value)),span=max-min||1;
 const points=ledger.map((r,i)=>({x:45+i/Math.max(1,ledger.length-1)*620,y:178-(r.value-min)/span*135,...r}));
 return <section className="tea-bi-dashboard investment-dashboard" aria-label="Project economics">
 <section className="economic-hero" data-domain="capital" aria-label="Capital investment overview"><div className="economic-hero-main"><div className="economic-heading"><h2>Capital investment</h2><button className="tea-bi-explore" onClick={()=>onExplore('capex')}>Inspect CAPEX ↗</button></div><div className="hero-total"><strong>{money(capex.total_capex)}</strong><span>{currency} · {basis}</span></div>{summaries(capital,'capex')}{allocation(capital,'capex')}<small>{rows(capex.issues).length?'Review capital scope':'Selected estimate · no uncertainty range established'}</small></div><RankedBars title="Equipment cost contribution" slices={equipment} currency={currency} basis="Purchased equipment costs" details={name=>rows(obj(stages.equipment?.result).equipment).filter(r=>String(r.equipment_tag)===name)} onExplore={()=>onExplore('capex')}/></section>
 <section className="economic-hero" data-domain="operating" aria-label="Operating costs overview"><div className="economic-hero-main"><div className="economic-heading"><h2>{opex.complete===false?'Known operating costs':'Operating costs'}</h2><button className="tea-bi-explore" onClick={()=>onExplore('opex')}>Inspect OPEX ↗</button></div><div className="hero-total"><strong>{money(annual.annual_cash_opex??annual.resolved_cash_subtotal)}</strong><span>{String(opex.currency??currency)} / year · operating year {lastYear}</span></div>{summaries([{name:'Fixed cash costs',value:num(annual.cash_fixed??annual.known_cash_fixed)},{name:'Variable cash costs',value:num(annual.cash_variable??annual.known_cash_variable)}],'opex')}{allocation([{name:'Fixed',value:num(annual.cash_fixed??annual.known_cash_fixed)??0},{name:'Variable',value:num(annual.cash_variable??annual.known_cash_variable)??0}],'opex')}</div><RankedBars title="Operating cost drivers" slices={operatingGrouped} currency={String(opex.currency??currency)} basis={`${opex.complete===false?'Known subtotal ·':'Annual cash costs ·'} operating year ${lastYear}`} details={name=>rows(annual.lines).filter(r=>r.accounting==='cash'&&String(r.category??r.id??'Operating item').replaceAll('_',' ')===name)} onExplore={()=>onExplore('opex')}/></section>
 <section className="economic-hero" data-domain="income" aria-label="Revenue overview">
 <div className="economic-hero-main">
  <div className="economic-heading"><h2>{revenue.complete===false?'Known revenue':'Revenue'}</h2><button className="tea-bi-explore" onClick={()=>onExplore('revenue')}>Inspect revenue ↗</button></div>
  <div className="hero-total"><strong>{money(revenueTotal.values[revenueIndex])}</strong><span>{revenueCurrency} / year · {revenueBasis}</span></div>
  {typeof revenue.price_basis_notice==='string'&&<p>{revenue.price_basis_notice}</p>}
  {allocation(commercial,'revenue')}
  {stages.revenue?.issues?.length?<p role="status">{stages.revenue.issues[0]}</p>:<small>Saved revenue calculation</small>}
 </div>
 <RankedBars title="Income contribution" slices={commercial} currency={revenueCurrency} basis={revenueBasis} hint="Select an income source to inspect its payment basis" details={name=>{
  const ids=new Set(streams.filter(stream=>stream.name===name).map(stream=>stream.id));
  return revenueRows.filter(row=>ids.has(row.product_id!=null?'product:'+row.product_id:'commercial:'+row.line_id));
 }} onExplore={()=>onExplore('revenue')}/>
 </section>
 {revenueYear&&<details className="tea-bi-chart rv-dashboard"><summary>Revenue trajectory and stream comparisons</summary><RevenueComparison config={obj(revenueConfig)} result={revenue} year={revenueYear} onYear={setSelectedRevenueYear} currency={revenueCurrency} onReview={()=>onExplore('revenue')}/></details>}
 <article className="tea-bi-chart tea-bi-cashflow"><div className="tea-bi-chart-head"><div><h3>Project cash flow</h3></div><div className="tea-bi-chart-actions"><div className="tea-bi-mode"><button aria-pressed={cashMode==='annual'} onClick={()=>{setCashMode('annual');setCashYear(null);}}>Annual</button><button aria-pressed={cashMode==='cumulative'} onClick={()=>{setCashMode('cumulative');setCashYear(null);}}>Cumulative</button></div><button className="tea-bi-explore" onClick={()=>onExplore('financial')}>Explore ↗</button></div></div>
 {points.length>1?<svg viewBox="0 0 710 215" className="tea-bi-line" role="img" aria-label={cashMode+' project cash flow by year'}>{[0,.5,1].map(t=><g key={t}><line x1="65" x2="665" y1={43+t*135} y2={43+t*135} className="cash-grid-line"/><text x="0" y={47+t*135} className="cash-axis-label">{fmt(max-t*span)}</text></g>)}<line x1="45" x2="665" y1={178-(0-min)/span*135} y2={178-(0-min)/span*135} stroke="currentColor" opacity=".2"/><polyline fill="none" stroke="#3578bd" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" points={points.map(p=>p.x+','+p.y).join(' ')}/>{points.map((p,i)=><circle key={i} cx={p.x} cy={p.y} r={cashYear===i?7:5} fill={p.value<0?'var(--negative)':'#3578bd'} tabIndex={0} role="button" aria-label={`Year ${p.year}: ${p.value.toLocaleString('en-GB')} ${currency}`} onMouseEnter={()=>setCashYear(i)} onFocus={()=>setCashYear(i)} onClick={()=>setCashYear(i)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setCashYear(i);}}}><title>Year {p.year}: {fmt(p.value)}</title></circle>)}<text x="45" y="206" fill="currentColor" fontSize="12">Year {points[0].year}</text><text x="595" y="206" fill="currentColor" fontSize="12">Year {points.at(-1)?.year}</text></svg>:<div className="tea-bi-empty">The saved financial model does not yet contain enough annual cash flow observations.</div>}<div className="cash-readout" aria-live="polite">{cashYear!==null&&points[cashYear]?<><span>Year {points[cashYear].year} · {cashMode} cash flow</span><strong data-negative={points[cashYear].value<0}>{points[cashYear].value.toLocaleString('en-GB',{maximumFractionDigits:2})} {currency}</strong></>:<span>Hover or focus a year to inspect cash flow.</span>}<small>{currency} · {basis}</small></div></article>
 </section>;
}
