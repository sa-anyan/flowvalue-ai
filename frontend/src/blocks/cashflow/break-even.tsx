import type {CashBreakEven} from './types';
export function recoveryYear(value?:CashBreakEven){if(value?.status!=='calculated'||value.year===null||value.year===undefined)return null;const year=Number(value.year);return Number.isFinite(year)&&year>=0?year:null;}
const label=(year:number)=>new Intl.NumberFormat('en-GB',{maximumFractionDigits:2}).format(year);
export function BreakEvenSummary({value,horizon}:{value?:CashBreakEven;horizon:number}){
 const year=recoveryYear(value);
 const status=year!==null?`Year ${label(year)}`:value?.status==='not_recovered'?`Not reached within ${horizon} years`:value?.status==='stale'?'Recalculate to update':value?.status==='undefined'?'Not applicable · no cumulative investment deficit':'Awaiting financial calculation';
 return <div className="cf-recovery-summary" role="status"><div><span>Cash break-even</span><strong>{status}</strong></div><small>First recovery of the project’s cumulative cash investment · undiscounted. Fractional years use linear interpolation; later losses can reverse recovery.</small></div>;
}
export function BreakEvenMarker({value,x,zeroY}:{value?:CashBreakEven;x:number;zeroY:number}){
 const year=recoveryYear(value);if(year===null||!Number.isFinite(x)||!Number.isFinite(zeroY))return null;
 const left=x>760;
 return <g className="cf-recovery-marker" aria-label={`Cash break-even at project year ${label(year)}`}><title>{`First cumulative cash recovery: project year ${label(year)}. Undiscounted; linear within-year interpolation.`}</title><line x1={x} x2={x} y1="40" y2="244" stroke="#a56b23" strokeWidth="1.5" strokeDasharray="5 5"/><circle cx={x} cy={zeroY} r="6" fill="#a56b23" stroke="var(--card)" strokeWidth="2"/><text x={x+(left?-10:10)} y="32" textAnchor={left?'end':'start'} style={{fill:'var(--ink)',fontSize:13,fontWeight:700}}>Break-even · year {label(year)}</text></g>;
}
