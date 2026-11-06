'use client';
import {useState} from 'react';
type Json=null|string|number|boolean|Json[]|{[key:string]:Json};
type Obj={[key:string]:Json};
export const revenueCategories=['product_sales','processing_services','capacity_availability','infrastructure_usage','environmental_attributes','other_contractual_income'];
export function RevenueEditor({config,calculated,onChange}:{config:Json;calculated?:Json;onChange:(value:Json)=>void}){
  const [error,setError]=useState('');
  const root=(config&&typeof config==='object'&&!Array.isArray(config)?config:{}) as Obj;
  const lines=(Array.isArray(root.commercial_lines)?root.commercial_lines:[]) as Obj[];
  const sales=(Array.isArray(root.sales)?root.sales:[]) as Obj[];
  function update(values:Obj[]){onChange({...root,commercial_lines:values});}
  function patch(index:number,change:Obj){update(lines.map((v,i)=>i===index?{...v,...change}:v));}
  function add(){
    const finance=root.financial as Obj|undefined;const life=Number(finance?.operating_years||1);
    if(!Number.isInteger(life)||life<1||life>50){setError('Set an operating life of 1–50 years first.');return;}
    const id=crypto.randomUUID();
    update([...lines,{id,name:'New commercial payment',category:'processing_services',payment_id:id,
      quantity_unit:'m3',rate_period:'per_unit',arrangement:'user_assumption',context_quote:'',
      rationale:'',uncertainty:'Unverified editable commercial assumption',source_references:[],
      stream_key:null,property:'contract_quantity',component:null,fixed_variable_distinct:false,
      eligibility_basis:'',years:Array.from({length:life},(_,i)=>({year:i+1,quantity:null,rate:null,
        fixed_payment:0,minimum_quantity:0,minimum_payment:0,availability:1,escalation:0,periods:1}))}]);
  }
  function reclassify(index:number,category:string){
    if(category==='product_sales')return;
    const sale=sales[index];const result=(calculated&&typeof calculated==='object'&&!Array.isArray(calculated)?calculated:{}) as Obj;
    const annual=(Array.isArray(result.products)?result.products:[]) as Obj[];
    const selected=annual.filter(y=>y.product_id===sale.id);
    const life=Number((root.financial as Obj|undefined)?.operating_years||1);
    if(selected.length!==life){setError('Calculate the existing product schedule before reclassifying it. Alternatively remove it and add a new payment.');return;}
    const moved:Obj={id:sale.id,name:sale.name,category,payment_id:sale.id,quantity_unit:sale.quantity_unit,
      rate_period:'per_unit',arrangement:'user_assumption',context_quote:sale.context_quote,
      rationale:'User reclassification of the last calculated sales schedule. Review billing quantities and rates: '+String(sale.rationale),
      uncertainty:'Copied last calculated annual scenario; not a contract or verified tariff',source_references:[],
      stream_key:null,property:'contract_quantity',component:null,fixed_variable_distinct:false,eligibility_basis:'',
      years:selected.map(y=>({year:y.year,quantity:y.quantity_sold,rate:y.net_selling_price,
        fixed_payment:0,minimum_quantity:0,minimum_payment:0,availability:1,escalation:0,periods:1}))};
    onChange({...root,sales:sales.filter((_,i)=>i!==index),commercial_lines:[...lines,moved]});setError('');
  }
  return <details open><summary>Revenue mechanisms and contracts</summary>
    <p>Each distinct payment appears once. Savings reduce an identified OPEX expense and are not sales. Save assumptions, then Run Python again; no LLM request is needed.</p>
    {sales.map((sale,i)=><div className="toolbar" key={String(sale.id)}><strong>Product sale · {String(sale.name)}</strong><label>Selling price ({String((root.price_basis as Obj|undefined)?.currency||'currency')}/{String(sale.quantity_unit||'unit')})<input type="number" min="0" step="any" aria-label={`Selling price for ${String(sale.name)}`} value={sale.unit_price===null?'':String(sale.unit_price??'')} onChange={e=>onChange({...root,sales:sales.map((s,j)=>j===i?{...s,unit_price:e.target.value===''?null:Number(e.target.value)}:s)})}/></label><label>Reclassify payment<select aria-label={`Category for ${String(sale.name)}`} value="product_sales" onChange={e=>reclassify(i,e.target.value)}>{revenueCategories.map(v=><option key={v} value={v}>{v.replaceAll('_',' ')}</option>)}</select></label><button className="secondary" onClick={()=>onChange({...root,sales:sales.filter((_,j)=>i!==j)})}>Remove product sale</button></div>)}
    {lines.map((line,i)=><fieldset key={String(line.id)}><legend>{String(line.name)}</legend>
      {['id','payment_id','name','quantity_unit','rationale','context_quote','eligibility_basis'].map(field=><label className="field" key={field}><span>{field.replaceAll('_',' ')}</span><input value={String(line[field]??'')} onChange={e=>patch(i,{[field]:e.target.value})}/></label>)}
      <label className="field"><span>Revenue category</span><select value={String(line.category)} onChange={e=>patch(i,{category:e.target.value})}>{revenueCategories.map(v=><option key={v} value={v}>{v.replaceAll('_',' ')}</option>)}</select></label>
      <label className="field"><span>Rate period</span><select value={String(line.rate_period)} onChange={e=>patch(i,{rate_period:e.target.value,years:(line.years as Obj[]).map(y=>({...y,periods:e.target.value==='monthly'?12:1}))})}>{['per_unit','annual','monthly'].map(v=><option key={v}>{v}</option>)}</select></label>
      <label className="field"><span>Arrangement</span><select value={String(line.arrangement)} onChange={e=>patch(i,{arrangement:e.target.value})}>{['user_assumption','user_confirmed','llm_proposed'].map(v=><option key={v}>{v}</option>)}</select></label>
      <label className="check"><input type="checkbox" checked={line.fixed_variable_distinct===true} onChange={e=>patch(i,{fixed_variable_distinct:e.target.checked})}/>Fixed and variable components have distinct payment scope</label>
      <label className="field"><span>Stream reference (blank for contract quantity)</span><input value={String(line.stream_key??'')} onChange={e=>patch(i,{stream_key:e.target.value||null,property:e.target.value?'volume_flow':'contract_quantity'})}/></label>
      <label className="field"><span>Source quantity property</span><select value={String(line.property)} onChange={e=>patch(i,{property:e.target.value})}>{['contract_quantity','volume_flow','mass_flow','component_mass_flow','component_volume_flow'].map(v=><option key={v}>{v}</option>)}</select></label>
      <p className="muted">Annual quantities are in the billing unit; annual/monthly rates add their stated time basis. Stream-linked quantities are recalculated from M&E and the operating schedule. Minimum payments are floors, not additional fees. Escalation is applied from operating year 1.</p>
      <div className="table-wrap"><table><thead><tr>{['Year','Quantity','Rate','Fixed payment','Minimum quantity','Minimum payment','Availability','Escalation'].map(v=><th key={v}>{v}</th>)}</tr></thead><tbody>{(line.years as Obj[]).map((year,j)=><tr key={String(year.year)}><td>{String(year.year)}</td>{['quantity','rate','fixed_payment','minimum_quantity','minimum_payment','availability','escalation'].map(field=><td key={field}><input aria-label={`${String(line.name)} year ${String(year.year)} ${field}`} type="number" step="any" value={year[field]===null?'':String(year[field])} onChange={e=>patch(i,{years:(line.years as Obj[]).map((v,k)=>j===k?{...v,[field]:e.target.value===''?null:Number(e.target.value)}:v)})}/></td>)}</tr>)}</tbody></table></div>
      <button className="secondary" onClick={()=>update(lines.filter((_,j)=>i!==j))}>Remove payment</button>
    </fieldset>)}
    <button className="secondary" onClick={add}>Add revenue payment</button>{error&&<p className="error">{error}</p>}
    <p className="muted">Source references, component names, avoided-cost targets and all legacy product assumptions remain editable in the structured section editor below.</p>
  </details>;
}
