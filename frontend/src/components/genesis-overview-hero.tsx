'use client';
import {useState} from 'react';
import Link from 'next/link';
import {assessmentHref} from '@/lib/assessment-navigation';
type Row=Record<string,unknown>;
const obj=(v:unknown):Row=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Row:{};
const list=(v:unknown):Row[]=>Array.isArray(v)?v.map(obj):[];
const number=(v:unknown):number|null=>v!==null&&v!==undefined&&v!==''&&typeof v!=='boolean'&&Number.isFinite(Number(v))?Number(v):null;
const format=(v:number|null)=>v===null?'Not calculated':new Intl.NumberFormat('en-GB',{notation:'compact',maximumFractionDigits:2}).format(v);
type Stages=Record<string,{result?:Row;result_is_stale?:boolean;status?:string}>;
type Point={year:string;annual:number|null;cumulative:number|null};
export function GenesisOverviewHero({stages,id}:{stages:Stages;id:string}){
 const [mode,setMode]=useState<'annual'|'cumulative'>('annual');
 const [selected,setSelected]=useState<number|null>(null);
 const capex=obj(stages.capex?.result),opex=obj(stages.opex?.result),revenue=obj(stages.revenue?.result),financial=obj(stages.financial?.result);
 const metrics=list(financial.metrics).length?list(financial.metrics):Array.isArray(financial.metrics)?(financial.metrics as unknown[]).filter(Array.isArray).map(v=>({name:(v as unknown[])[0],...obj((v as unknown[])[1])})):[];
 const npv=metrics.find(m=>m.name==='project_npv');
 const led=list(financial.ledger);
 const points:Point[]=led.map((r,i)=>({year:String(r.year??i+1),annual:number(r.fcff??r.project_cash_flow),cumulative:number(r.cumulative_project_cash)}));
 const plotted=points.filter(p=>(mode==='annual'?p.annual:p.cumulative)!==null);
 const values=plotted.map(p=>(mode==='annual'?p.annual:p.cumulative) as number);
 const lowest=Math.min(0,...values),highest=Math.max(0,...values),span=highest-lowest||1;
 const chartPoints=plotted.map((p,i)=>({x:64+i/Math.max(1,plotted.length-1)*640,y:220-((values[i]-lowest)/span)*168,...p,value:values[i]}));
 const currency=String(financial.currency??capex.currency??'Currency unavailable');
 const revenueCurrency=String(obj(revenue.basis).currency??revenue.currency??currency);
 const opexCurrency=String(opex.currency??currency);
 const opexYears=obj(opex.years);
 const latestYear=Object.keys(opexYears).sort((a,b)=>Number(a)-Number(b)).at(-1);
 const cashOpex=latestYear?number(obj(opexYears[latestYear]).annual_cash_opex??obj(opexYears[latestYear]).resolved_cash_subtotal):null;
 const revenueYears=list(revenue.annual);
 const matchingRevenue=revenueYears.find(r=>String(r.year)===latestYear);
 const cashRevenue=number(matchingRevenue?.sales_revenue);
 const comparable=latestYear!==undefined&&currency===opexCurrency&&currency===revenueCurrency&&cashRevenue!==null&&cashOpex!==null&&cashRevenue>=0&&cashOpex>=0;
 const scale=comparable?Math.max(cashRevenue!,cashOpex!,1):1;
 const capexValue=number(capex.total_capex);
 const npvValue=number(npv?.value);
 const [active,setActive]=useState<'all'|'capex'|'financial'>('all');
 return <div className="genesis-overview-hero">
  <div className="genesis-hero-toolbar" aria-label="Dashboard display options"><span className="genesis-hero-toolbar-label">View</span>{([['all','Overview'],['capex','Capital'],['financial','Financial']] as const).map(([key,label])=><button key={key} type="button" aria-pressed={active===key} onClick={()=>setActive(key)}>{label}</button>)}</div>
  <div className="genesis-hero-heading"><div><p className="genesis-hero-kicker">PROJECT ANALYTICS</p><h2>TEA overview</h2><p>Investment, operating performance and modelled project cash flow</p></div><span className="genesis-hero-basis">{currency} · Saved assessment</span></div>
  <div className="genesis-hero-trio">
   <Link className="genesis-hero-card genesis-hero-metric" href={assessmentHref('/capex',id)} data-active={active==='capex'}>
    <div className="genesis-hero-card-head"><span className="genesis-hero-symbol" aria-hidden="true">◈</span><div><h3>Capital investment</h3><p>{capex.complete===false?'Known subtotal · incomplete scope':'Saved calculation'}</p></div></div>
    <strong title={capexValue===null?undefined:capexValue.toLocaleString('en-GB')}>{format(capexValue)}</strong><span className="genesis-hero-unit">{currency} · {capexValue===null?'Not calculated':'Total CAPEX'}</span>
    <span className="genesis-hero-card-foot">Inspect capital basis <span aria-hidden="true">↗</span></span>
   </Link>
   <div className="genesis-hero-card genesis-hero-comparison" data-active={active==='all'}>
    <div className="genesis-hero-card-head"><span className="genesis-hero-symbol" aria-hidden="true">▥</span><div><h3>Operating comparison</h3><p>{latestYear?'Modelled operating year '+latestYear:'Model year unavailable'}</p></div></div>
    {comparable?<div className="genesis-hero-comparison-bars"><div><span>Revenue <b>{format(cashRevenue)}</b></span><div className="genesis-hero-track"><i style={{width:(cashRevenue!/scale*100)+'%'}}/></div></div><div><span>Cash OPEX <b>{format(cashOpex)}</b></span><div className="genesis-hero-track"><i style={{width:(cashOpex!/scale*100)+'%'}}/></div></div></div>:<p className="genesis-hero-empty">Comparable annual revenue and operating costs are not available on the same currency and year basis.</p>}
    <span className="genesis-hero-card-foot">{comparable?currency+' / year':'Requires comparable saved results'}</span>
   </div>
   <Link className="genesis-hero-card genesis-hero-metric genesis-hero-npv" href={assessmentHref('/financial-modelling',id)} data-active={active==='financial'}>
    <div className="genesis-hero-card-head"><span className="genesis-hero-symbol" aria-hidden="true">⌁</span><div><h3>Net present value</h3><p>Discounted project lifetime</p></div></div>
    <strong title={npvValue===null?undefined:npvValue.toLocaleString('en-GB')} data-negative={npvValue!==null&&npvValue<0}>{format(npvValue)}</strong><span className="genesis-hero-unit">{currency} · {npvValue===null?'Not calculated':'Project NPV'}</span>
    <span className="genesis-hero-card-foot">Inspect financial model <span aria-hidden="true">↗</span></span>
   </Link>
  </div>
  <section className="genesis-hero-wide" aria-label="Project cash flow chart">
   <div className="genesis-hero-wide-top"><div><h3>Project cash flow</h3><p>Calculated cash-flow trajectory by model year</p></div><div className="genesis-hero-mode" aria-label="Cash flow display"><button aria-pressed={mode==='annual'} onClick={()=>{setMode('annual');setSelected(null)}}>Annual</button><button aria-pressed={mode==='cumulative'} onClick={()=>{setMode('cumulative');setSelected(null)}}>Cumulative</button></div></div>
   <div className="genesis-hero-legend"><span><i/> {mode==='annual'?'Annual project cash flow':'Cumulative project cash flow'}</span><span>{currency} · saved Python ledger</span></div>
   {chartPoints.length>1?<><svg className="genesis-hero-line-chart" viewBox="0 0 760 270" role="group" aria-label={mode+' cash flow chart; keyboard accessible year data points'}>
    {[0,.25,.5,.75,1].map(t=><g key={t}><line x1="64" x2="704" y1={52+t*168} y2={52+t*168} className="genesis-hero-grid"/><text x="4" y={56+t*168} className="genesis-hero-axis">{format(highest-t*span)}</text></g>)}
    <line x1="64" x2="704" y1={220-(0-lowest)/span*168} y2={220-(0-lowest)/span*168} className="genesis-hero-zero"/>
    <polyline className="genesis-hero-line" points={chartPoints.map(p=>p.x+','+p.y).join(' ')}/>
    {chartPoints.map((p,i)=><circle key={p.year+':'+i} cx={p.x} cy={p.y} r={selected===i?6:4} className="genesis-hero-point" tabIndex={0} role="button" aria-label={`Year ${p.year}: ${p.value.toLocaleString('en-GB')} ${currency}`} onFocus={()=>setSelected(i)} onMouseEnter={()=>setSelected(i)} onClick={()=>setSelected(i)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setSelected(i)}}}><title>{`Year ${p.year}: ${p.value.toLocaleString('en-GB')} ${currency}`}</title></circle>)}
    <text x="64" y="252" className="genesis-hero-axis">Year {chartPoints[0].year}</text><text x="620" y="252" className="genesis-hero-axis">Year {chartPoints.at(-1)?.year}</text>
   </svg><p className="genesis-hero-readout" aria-live="polite">{selected!==null&&chartPoints[selected]?`Year ${chartPoints[selected].year} · ${chartPoints[selected].value.toLocaleString('en-GB')} ${currency}`:'Hover or focus a point to inspect its calculated value.'}</p></>:<div className="genesis-hero-chart-empty">Not enough saved annual cash flow observations to draw a financial trajectory.</div>}
  </section>
  <details className="genesis-hero-details"><summary>Explore all six financial indicators and detailed cost charts</summary></details>
 </div>;
}
