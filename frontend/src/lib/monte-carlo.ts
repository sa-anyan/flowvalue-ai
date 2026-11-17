export type Parameter={id:string;label:string;baseline?:number|string|null;choice_labels?:Record<string,string>;enabled:boolean;targets:(string|number)[][];unit:string;distribution:string;minimum:number|null;mode:number|null;maximum:number|null;stddev:number|null;choices:(number|string)[];probabilities:number[];source:string;rationale:string;uncertainty:string;confidence:string;kind:string;review_required?:string;hard_min:number|null;hard_max:number|null;strictly_positive:boolean};
export type Settings={parameters:Parameter[];iterations:number;seed:number;operating_years:number;target_irr:number;label:string;baseline_revision:number|null;distinct:{equipment_key:string;rationale:string}[];correlations:{a:string;b:string;rho:number;rationale:string}[];aliases:{equipment_key:string;target_key:string;rationale:string}[]};
export type Row=Record<string,unknown>;
export type Job={id:string;status:string;completed:number;total:number;summary:Row|null;settings:Settings;preflight?:Row;error?:string};

export async function mcApi(path:string,options?:RequestInit){const r=await fetch('/api/'+path,{cache:'no-store',...options});const v=await r.json();if(!r.ok)throw new Error(typeof v.detail==='string'?v.detail:Array.isArray(v.detail)?v.detail.map((d:{loc?:unknown[];msg?:string})=>`${d.loc?.join(' › ')}: ${d.msg}`).join('; '):'Monte Carlo request failed');return v;}

/* Inputs without a published or AI range: optional default ±x% (user's choice, labelled). */
export const PERCENT_SOURCE='Default ±';
export const hasRange=(p:Parameter)=>p.kind==='configuration'||(p.minimum!==null&&p.maximum!==null&&p.minimum<p.maximum);
export const percentApplied=(p:Parameter)=>p.source.startsWith(PERCENT_SOURCE);
export const appliedPercent=(p:Parameter)=>Number(p.source.slice(PERCENT_SOURCE.length).split('%')[0])||null;
export const baseValue=(p:Parameter)=>{const v=p.mode??(typeof p.baseline==='number'?p.baseline:Number(p.baseline));return typeof v==='number'&&Number.isFinite(v)?v:null;};
/** Range of ±pct% around the baseline, kept inside hard limits. Null when there is no non-zero baseline. */
export function percentRange(p:Parameter,pct:number):Partial<Parameter>|null{
 const base=baseValue(p);if(base===null||base===0||!(pct>0)||p.kind==='configuration')return null;
 let low=base*(1-pct/100),high=base*(1+pct/100);if(low>high)[low,high]=[high,low];
 if(p.hard_min!==null)low=Math.max(low,p.hard_min);if(p.hard_max!==null)high=Math.min(high,p.hard_max);
 if(p.strictly_positive&&low<=0)low=Math.min(base,high)/2;
 const round=(v:number)=>Number(v.toPrecision(6));
 if(!(low<high))return null;
 return{minimum:round(low),mode:base,maximum:round(high),distribution:'triangular',enabled:true,
  source:`${PERCENT_SOURCE}${pct}% (no published or AI range)`,rationale:`Varied ±${pct}% around the saved value by your choice; not a sourced range.`};
}
