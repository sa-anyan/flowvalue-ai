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
type Point={year:number;annual:number|null;cumulative:number|null};
export function GenesisOverviewHero({stages,id}:{stages:Stages;id:string}){
 const [mode,setMode]=useState<'annual'|'cumulative'>('annual');
 const [selected,setSelected]=useState<number|null>(null);
 const capex=obj(stages.capex?.result),opex=obj(stages.opex?.result),revenue=obj(stages.revenue?.result),financial=obj(stages.financial?.result);
 const metrics=Array.isArray(financial.metrics)?financial.metrics.filter(Array.isArray):[];
 const npv=obj(metrics.find(metric=>metric[0]==='project_npv')?.[1]);
 const led=list(financial.ledger);
 const points:Point[]=led.flatMap(r=>{
  const year=number(obj(r.period).year ?? r.year);
  return year===null?[]:[{year,annual:number(r.fcff??r.project_cash_flow),cumulative:number(r.cumulative_project_cash)}];
 }).sort((a,b)=>a.year-b.year);
 const firstYear=points[0]?.year??0,lastYear=points.at(-1)?.year??firstYear;
 const values=points.flatMap(p=>p[mode]===null?[]:[p[mode]]);
 const lowest=Math.min(0,...values),highest=Math.max(0,...values),span=highest-lowest||1;
 const segments:{x:number;y:number}[][]=[];
 const chartPoints=points.flatMap((p,i)=>{
  const value=p[mode];
  if(value===null)return [];
  const x=64+(p.year-firstYear)/Math.max(1,lastYear-firstYear)*640;
  const y=220-(value-lowest)/span*168;
  const previous=points[i-1];
  if(!previous||previous[mode]===null||p.year-previous.year!==1)segments.push([]);
  segments.at(-1)!.push({x,y});
  return [{...p,x,y,value}];
 });
 const trend=points.filter(p=>p.annual!==null);
 const trendValues=trend.map(p=>p.annual!);
 const trendMin=Math.min(...trendValues),trendMax=Math.max(...trendValues);
 const capexStale=stages.capex?.result_is_stale===true||stages.capex?.status==='stale';
 const financialStale=stages.financial?.result_is_stale===true||stages.financial?.status==='stale';
 const currency=String(financial.currency??'Currency unavailable');
 const revenueCurrency=obj(revenue.basis).currency??revenue.currency;
 const opexCurrency=opex.currency;
 const opexYears=obj(opex.years);
 const latestYear=Object.keys(opexYears).sort((a,b)=>Number(a)-Number(b)).at(-1);
 const cashOpex=latestYear?number(obj(opexYears[latestYear]).annual_cash_opex??obj(opexYears[latestYear]).resolved_cash_subtotal):null;
 const revenueYears=list(revenue.annual);
 const matchingRevenue=revenueYears.find(r=>String(r.year)===latestYear);
 const cashRevenue=number(matchingRevenue?.sales_revenue);
 const revenuePeriod=obj(revenue.basis).price_period;
 const comparable=latestYear!==undefined&&typeof opexCurrency==='string'&&opexCurrency===revenueCurrency&&typeof opex.price_period==='string'&&opex.price_period===revenuePeriod&&cashRevenue!==null&&cashOpex!==null&&cashRevenue>=0&&cashOpex>=0;
 const scale=comparable?Math.max(cashRevenue!,cashOpex!,1):1;
 const capexValue=number(capex.total_capex);
 const npvValue=number(npv?.value);
 return <div className="genesis-overview-hero">
  <nav className="genesis-hero-toolbar" aria-label="Analytics destinations"><span className="genesis-hero-toolbar-label">Explore</span><span className="genesis-hero-active" aria-current="page">Overview</span><Link href={assessmentHref('/capex',id)}>Capital</Link><Link href={assessmentHref('/financial-modelling',id)}>Financial</Link></nav>
  <div className="genesis-hero-heading"><div><p className="genesis-hero-kicker">PROJECT ANALYTICS</p><h1>TEA overview</h1><p>Investment, operating performance and modelled project cash flow</p></div><span className="genesis-hero-basis">{currency} · Saved assessment</span></div>
  <div className="genesis-hero-trio">
   <Link className="genesis-hero-card genesis-hero-metric" href={assessmentHref('/capex',id)}>
    <div className="genesis-hero-card-head"><span className="genesis-hero-symbol" aria-hidden="true">◈</span><div><h3>Capital investment</h3><p>{capexStale?'Stale · recalculation required':capex.complete===false?'Known subtotal · incomplete scope':'Saved calculation'}</p></div></div>
    <strong title={capexValue===null?undefined:capexValue.toLocaleString('en-GB')}>{format(capexValue)}</strong><span className="genesis-hero-unit">{String(capex.currency??'Currency unavailable')} · {capexValue===null?'Not calculated':capex.complete===false?'Known CAPEX subtotal':'Total CAPEX'}</span>
    <span className="genesis-hero-card-foot">Inspect capital basis <span aria-hidden="true">↗</span></span>
   </Link>
   <div className="genesis-hero-card genesis-hero-comparison">
    <div className="genesis-hero-card-head"><span className="genesis-hero-symbol" aria-hidden="true">▥</span><div><h3>Operating comparison</h3><p>{latestYear?'Modelled operating year '+latestYear:'Model year unavailable'}</p></div></div>
    {comparable?<div className="genesis-hero-comparison-bars"><div><span>Revenue <b>{format(cashRevenue)}</b></span><div className="genesis-hero-track"><i style={{height:(cashRevenue!/scale*100)+'%'}}/></div></div><div><span>Cash OPEX <b>{format(cashOpex)}</b></span><div className="genesis-hero-track"><i style={{height:(cashOpex!/scale*100)+'%'}}/></div></div></div>:<p className="genesis-hero-empty">Comparable annual revenue and operating costs are not available on the same currency, price period and year basis.</p>}
    <span className="genesis-hero-card-foot">{comparable?opexCurrency+' / year · '+String(opex.price_period):'Requires comparable saved results'}</span>
   </div>
   <Link className="genesis-hero-card genesis-hero-metric genesis-hero-npv" href={assessmentHref('/financial-modelling',id)}>
    <div className="genesis-hero-card-head"><span className="genesis-hero-symbol" aria-hidden="true">⌁</span><div><h3>Net present value</h3><p>{financialStale?'Stale · recalculation required':'Discounted project lifetime'}</p></div></div>
    <strong title={npvValue===null?undefined:npvValue.toLocaleString('en-GB')} data-negative={npvValue!==null&&npvValue<0}>{format(npvValue)}</strong><span className="genesis-hero-unit">{currency} · {npvValue===null?'Not calculated':'Project NPV'}</span>
    {trend.length>1&&<svg viewBox="0 0 220 42" className="genesis-hero-spark" role="img" aria-label="Saved annual project cash flow trend">
     {points.slice(1).map((p,i)=>{
      const before=points[i];
      if(p.annual===null||before.annual===null||p.year-before.year!==1)return null;
      const tx=(year:number)=>4+(year-firstYear)/Math.max(1,lastYear-firstYear)*212;
      const ty=(v:number)=>38-(v-trendMin)/(trendMax-trendMin||1)*32;
      return <line key={i} x1={tx(before.year)} x2={tx(p.year)} y1={ty(before.annual)} y2={ty(p.annual)}/>;
     })}
    </svg>}
    <span className="genesis-hero-card-foot">Inspect financial model <span aria-hidden="true">↗</span></span>
   </Link>
  </div>
  <section className="genesis-hero-wide" aria-label="Project cash flow chart">
   <div className="genesis-hero-wide-top"><div><h3>Project cash flow</h3><p>{financialStale?'Saved cash flow is stale · recalculate to update':'Calculated cash-flow trajectory by model year'}</p></div><div className="genesis-hero-mode" aria-label="Cash flow display"><button aria-pressed={mode==='annual'} onClick={()=>{setMode('annual');setSelected(null)}}>Annual</button><button aria-pressed={mode==='cumulative'} onClick={()=>{setMode('cumulative');setSelected(null)}}>Cumulative</button></div></div>
   <div className="genesis-hero-legend"><span><i/> {mode==='annual'?'Annual project cash flow':'Cumulative project cash flow'}</span><span>{currency} · saved Python ledger</span></div>
   {chartPoints.length>1?<><svg className="genesis-hero-line-chart" viewBox="0 0 760 270" role="group" aria-label={mode+' cash flow chart; keyboard accessible year data points'}>
    {[0,.25,.5,.75,1].map(t=><g key={t}><line x1="64" x2="704" y1={52+t*168} y2={52+t*168} className="genesis-hero-grid"/><text x="4" y={56+t*168} className="genesis-hero-axis">{format(highest-t*span)}</text></g>)}
    <line x1="64" x2="704" y1={220-(0-lowest)/span*168} y2={220-(0-lowest)/span*168} className="genesis-hero-zero"/>
    <g key={mode} className="genesis-hero-series">{segments.map((segment,i)=><polyline key={i} className="genesis-hero-line" points={segment.map(p=>p.x+','+p.y).join(' ')}/>)}</g>
    {chartPoints.map((p,i)=><circle key={p.year+':'+i} cx={p.x} cy={p.y} r={selected===i?6:4} className="genesis-hero-point" tabIndex={0} role="button" aria-label={`Year ${p.year}: ${p.value.toLocaleString('en-GB')} ${currency}`} onFocus={()=>setSelected(i)} onMouseEnter={()=>setSelected(i)} onClick={()=>setSelected(i)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setSelected(i)}}}><title>{`Year ${p.year}: ${p.value.toLocaleString('en-GB')} ${currency}`}</title></circle>)}
    <text x="64" y="252" className="genesis-hero-axis">Year {chartPoints[0].year}</text><text x="620" y="252" className="genesis-hero-axis">Year {chartPoints.at(-1)?.year}</text>
   </svg><p className="genesis-hero-readout" aria-live="polite">{selected!==null&&chartPoints[selected]?`Year ${chartPoints[selected].year} · ${chartPoints[selected].value.toLocaleString('en-GB')} ${currency}`:'Hover or focus a point to inspect its calculated value.'}</p></>:<div className="genesis-hero-chart-empty">Not enough saved annual cash flow observations to draw a financial trajectory.</div>}
  </section>
 </div>;
}
