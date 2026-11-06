'use client';
type Json=null|string|number|boolean|Json[]|{[key:string]:Json};
type Row=Record<string,Json>;
export const thermalParameters=[
 ...['hot_inlet','hot_outlet','cold_inlet','cold_outlet'].map(role=>({name:role+'_temperature_k',unit:'K'})),
 {name:'heat_duty_kw',unit:'kW'},{name:'specific_heat_kj_kg_k',unit:'kJ/kg/K'},
 {name:'latent_heat_kj_kg',unit:'kJ/kg'},{name:'phase_change_fraction',unit:'fraction'},
 {name:'sensible_enthalpy_change_kj_kg',unit:'kJ/kg'},{name:'utility_allocation_fraction',unit:'fraction'},
 {name:'duty_balance_tolerance_fraction',unit:'fraction'},
];
type Measurement={id:string;entity_key:string;property:string;value:number;unit:string;sheet:string;cell:string;status?:string};
const object=(value:Json):Row=>value&&typeof value==='object'&&!Array.isArray(value)?value:{};
const label=(s:string)=>s.replaceAll('_',' ');
export function ThermalBasis({basis,streams,measurements=[],onChange}:{basis:Row;streams:{entity_key:string;tag:string}[];measurements?:Measurement[];onChange:(basis:Row)=>void}){
 const choices=Array.isArray(basis.source_choices)?basis.source_choices.map(object):[];
 return <details open><summary>Thermal duty & stream basis</summary>
 <p>Preliminary thermal scenario. Source readings stay unchanged. Select a source-cell basis when readings conflict. Conflicting side duties remain visible; this does not certify an energy balance.</p>
 {['hot_inlet','hot_outlet','cold_inlet','cold_outlet'].map(role=><div key={role}>
 <label className="field">{label(role)} stream<select value={String(basis[role+'_stream_key']??'')} onChange={e=>onChange({...basis,[role+'_stream_key']:e.target.value||null,source_choices:choices.filter(c=>c.role!==role)})}><option value="">Missing / explicit temperature assumption</option>{streams.map(s=><option key={s.entity_key} value={s.entity_key}>{s.tag}</option>)}</select></label>
 {['temperature','enthalpy_flow','mass_flow'].map(property=>{
  const observations=measurements.filter(m=>m.entity_key===basis[role+'_stream_key']&&m.property===property);
  const chosen=choices.find(c=>c.role===role&&c.property===property);
  if(observations.length<2&&!chosen)return null;
  return <label className="field" key={property}>{label(role)} {label(property)} source<select value={String(chosen?.measurement_id??'')} onChange={e=>onChange({...basis,source_choices:[...choices.filter(c=>c.role!==role||c.property!==property),...(e.target.value?[{role,property,measurement_id:e.target.value,rationale:'User-selected source observation for this scenario; alternatives retained.'}]:[])]})}><option value="">Automatic source precedence / review conflict</option>{observations.map(m=><option key={m.id} value={m.id}>{m.value} {m.unit} · {m.sheet}!{m.cell} · {m.status??'source'}</option>)}</select>{chosen&&<small>{String(chosen.rationale??'')}</small>}</label>;
 })}</div>)}
 {Object.entries({duty_side:['hot','cold'],duty_method:['enthalpy_difference','sensible_heat','phase_change','assumed_duty'],flow_arrangement:['countercurrent','parallel','explicit_lmtd'],phase_change:['none','hot_condensing','cold_boiling','both'],duty_conflict_policy:['provisional_selected_side','require_consistency']}).map(([name,values])=><label className="field" key={name}>{label(name)}<select value={String(basis[name]??'')} onChange={e=>onChange({...basis,[name]:e.target.value})}><option value="">Select basis</option>{values.map(v=><option key={v} value={v}>{label(v)}</option>)}</select></label>)}
 {['common_enthalpy_reference_confirmed','steady_state_mass_flow_assumed'].map(name=><label className="check" key={name}><input type="checkbox" checked={basis[name]===true} onChange={e=>onChange({...basis,[name]:e.target.checked})}/>{label(name)}</label>)}
 <label className="field">Thermal rationale<textarea value={String(basis.rationale??'')} onChange={e=>onChange({...basis,rationale:e.target.value})}/></label>
 <p>{String(basis.limitations??'')}</p>
 </details>;
}
