'use client';
import {useRef} from 'react';

/** Sliders edit canonical draft fields; they never calculate revenue in the browser. */
export function RevenueSlider({label,value,onChange,fraction=false}: {
 label:string;value:unknown;onChange:(value:number)=>void;fraction?:boolean;
}) {
 const numeric=value===null||value===undefined||value===''?null:Number(value);
 const initial=useRef(Number.isFinite(numeric)&&numeric!==null&&numeric>0?numeric:100);
 if(numeric===null||!Number.isFinite(numeric)||numeric<0)return null;
 const max=fraction?1:Math.max(initial.current*2,numeric);
 return <div className="rev-slider"><div className="rev-slider-head"><span>{label}</span><strong>{fraction?`${Math.round(numeric*100)}%`:new Intl.NumberFormat('en-GB',{maximumFractionDigits:4}).format(numeric)}</strong></div><input type="range" aria-label={`${label} slider`} min={0} max={max} step={fraction?.01:Math.max(max/1000,.000001)} value={numeric} onChange={e=>onChange(Number(Number(e.target.value).toPrecision(8)))}/><small>{fraction?'0–100%':'Drag to adjust · use the number field for an exact value'}</small></div>;
}
