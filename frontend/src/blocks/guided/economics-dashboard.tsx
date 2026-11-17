'use client';

import {useEffect, useRef} from 'react';
import {compact, num} from '@/lib/guided-flow';

export function useLiveEconomics(signature: string, enabled: boolean, run: () => Promise<unknown>) {
  const latest = useRef(run);
  const attempted = useRef('');
  latest.current = run;
  useEffect(() => {
    if (!enabled || !signature || attempted.current === signature) return;
    const timer = window.setTimeout(() => {
      attempted.current = signature;
      void latest.current();
    }, 750);
    return () => window.clearTimeout(timer);
  }, [signature, enabled]);
}

const colors = ['#087e9c', '#25856c', '#99702e', '#7855a6', '#49718f', '#a75351'];

export function EconomicsComposition({title, values, currency}: {
  title: string; values: Array<[string, unknown]>; currency?: string;
}) {
  const rows = values.map(([label,value]) => ({label, value:num(value)}));
  const positive = rows.map((row,index) => ({...row,index})).filter(row => row.value !== null && row.value > 0);
  const total = positive.reduce((sum,row) => sum + (row.value ?? 0), 0);
  const peak = Math.max(0, ...rows.map(row => Math.abs(row.value ?? 0)));
  let end = 0;
  const slices = positive.map(row => {
    const start = end;
    end += (row.value ?? 0) / total * 100;
    return `${colors[row.index % colors.length]} ${start}% ${end}%`;
  });
  const showPie = slices.length > 0 && rows.every(row => row.value !== null && row.value >= 0);
  return <section className="gf-card-block gf-economics-chart" aria-label={title}>
    <h2>{title}</h2>
    {currency && <small>{currency}</small>}
    {showPie && <div aria-hidden="true" className="gf-economics-pie" style={{backgroundImage:`conic-gradient(${slices.join(', ')})`}} />}
    {rows.length ? <ul>
      {rows.map(({label,value},index) => <li key={index}>
        <div><span>{label}</span><strong>{value === null ? 'Pending' : compact(value)}</strong></div>
        {value !== null && <div className="gf-economics-track" aria-hidden="true"><i style={{width:`${peak ? Math.abs(value) / peak * 100 : 0}%`, background:value < 0 ? 'var(--gf-neg)' : colors[index % colors.length]}} /></div>}
      </li>)}
    </ul> : <p className="gf-muted">No calculated values to chart yet.</p>}
  </section>;
}

/** Plot only the model years and values actually present in the Python result. */
export function EconomicsTrend({title, values, currency}: {
  title: string; values: Array<[unknown, unknown]>; currency?: string;
}) {
  const years = values.flatMap(([year,value]) => {
    const key = num(year);
    return key === null ? [] : [{year:key,value:num(value)}];
  }).sort((a,b) => a.year - b.year);
  const points = years.filter((row): row is {year:number;value:number} => row.value !== null);
  if (points.length < 2) return null;

  const min = Math.min(0,...points.map(row => row.value));
  const max = Math.max(0,...points.map(row => row.value));
  const first = years[0].year;
  const last = years[years.length - 1].year;
  const x = (year:number) => 46 + (year - first) / Math.max(1,last-first) * 280;
  const y = (value:number) => 100 - (value-min) / (max-min || 1) * 85;

  return <section className="gf-card-block gf-economics-chart" aria-label={title}>
    <h2>{title}</h2>
    {currency && <small>{currency}</small>}
    <svg className="gf-economics-trend" viewBox="0 0 352 126" role="img" aria-label={title + ' by operating year'}>
      <line x1={46} x2={326} y1={y(0)} y2={y(0)} stroke="var(--gf-line)" />
      {years.slice(1).map((row,index) => {
        const before = years[index];
        return row.value === null || before.value === null || row.year !== before.year+1 ? null
          : <line key={index} x1={x(before.year)} y1={y(before.value)} x2={x(row.year)} y2={y(row.value)} stroke="currentColor" strokeWidth={2} />;
      })}
      {points.map((row,index) => <circle key={index} cx={x(row.year)} cy={y(row.value)} r={3} fill="currentColor"><title>{`Year ${row.year}: ${compact(row.value)} ${currency ?? ''}`}</title></circle>)}
      <text x={46} y={120}>Year {first}</text><text x={326} y={120} textAnchor="end">Year {last}</text>
    </svg>
    <details><summary>Values by operating year</summary><ul>
      {years.map((row,index) => <li key={index}><div><span>Year {row.year}</span><strong>{row.value === null ? 'Pending' : compact(row.value)}</strong></div></li>)}
    </ul></details>
  </section>;
}
