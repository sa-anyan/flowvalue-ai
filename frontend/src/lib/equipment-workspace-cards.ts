import type {EquipmentCard} from '@/blocks/equipment/view';
import {findEquipmentSizingTrace, type EquipmentSizingTrace} from './equipment-sizing-traces';
import {equipmentMapping as findMapping, list as rows, obj as record, type Row} from './guided-flow';

/** The advanced and guided directories project the same saved equipment costs and source scope. */
export function equipmentWorkspaceCards(state: Row | null, plan: unknown): EquipmentCard[] {
  if (!state) return [];
  const report=record(state.scoped_report||state.effective_report||record(state.parsed).report);
  const equipment=rows(record(record(record(record(state.results).stages).equipment).result).equipment);
  const equipEntities=rows(report.entities).filter(e=>e.kind==='equipment').flatMap(e=>{
    const parent=rows(plan).find(r=>r.equipment_key===e.key);
    const children=rows(parent?.physical_assets);
    if(!children.length||record(parent?.scope_confirmation).status!=='user_confirmed') return [e];
    return children.map(child=>({...e,key:String(e.key)+'::'+String(child.asset_id),identifier:String(child.equipment_tag||e.identifier),values:rows(e.values).filter(v=>Array.isArray(child.source_value_ids)&&child.source_value_ids.includes(String(v.id)))}));
  }).map(e=>({...e,key:String(e.key),identifier:String(e.identifier),values:rows(e.values)}));
  const equipmentMapping=(key:string)=>findMapping(plan,key);
  return (equipment?.length?equipment:equipEntities.map(e=>({equipment_tag:e.identifier,equipment_key:e.key,status:'unresolved'} as Row))).map((row,i)=>{
    const tag=String(row.equipment_tag??row.tag??'Equipment '+(i+1));
    const sourceKey=record(row.parsed_source).equipment_key??row.equipment_key;
    const equipmentKey=typeof sourceKey==='string'?sourceKey:undefined;
    const entity=equipmentKey?equipEntities.find(e=>e.key===equipmentKey):equipEntities.find(e=>e.identifier===tag);
    const reviewedValues=[...(entity?.values??[])].reverse();
    const classification=reviewedValues.find(v=>v.property==='type')?.normalized_value;
    const name=reviewedValues.find(v=>v.property==='name')?.normalized_value??classification??reviewedValues.find(v=>v.property==='description')?.normalized_value;
    const mapping=equipmentMapping(entity?.key||'');
    const concept=record(mapping.matching);
    const familyNames=Array.from(new Set(rows(concept.candidate_models).map(m=>String(m.equipment_name??'')))).filter(Boolean).join(', ');
    const purchase=row.equipment_cost??record(row.reference_cost).purchase_cost;
    const installation=row.installation_cost;
    const capital=row.cost_scope==='unit_capital'||(record(record(row.calculation).evidence).source==='openpytea'&&['installed_equipment','module_estimate'].includes(String(row.cost_scope)));
    const cost=capital?row.amount:row.equipment_and_installation_cost;
    const costEvidence=record(record(row.calculation).evidence);
    const translation=record(costEvidence.cost_translation);
    const lineage=[String(record(costEvidence.model_metadata).reference??''),String(record(costEvidence.model_metadata).range_status??''),translation.notice?String(translation.source_period)+' → '+String(translation.target_period)+': '+String(translation.notice):''].filter(Boolean).join(' · ');
    const money=(v:unknown)=>v!==null&&v!==undefined&&Number.isFinite(Number(v))?Number(v).toLocaleString('en-GB',{maximumFractionDigits:2}):'Not available';
    const calculatedSize=record(record(row.calculation).estimate);
    const displayedSize=mapping?.manual_price?mapping.size:calculatedSize.size??mapping?.size;
    const displayedUnit=mapping?.manual_price?mapping.size_unit:calculatedSize.size_unit??mapping?.size_unit;
    return {key:equipmentKey??entity?.key??tag,tag,sizingTrace:findEquipmentSizingTrace(state.equipment_sizing_traces as EquipmentSizingTrace[] | undefined,equipmentKey??entity?.key),name:String(name??row.equipment_type??row.description??'Equipment'),type:String(classification??row.equipment_type??name??'Not specified'),size:displayedSize!==undefined&&displayedSize!==null?String(displayedSize)+' '+String(displayedUnit??''):'Size not specified',capitalBasis:capital,costBasis:String(row.cost_scope??''),calculationTrace:costEvidence.source==='openpytea'?JSON.stringify({model_id:row.curve_id,source_commit:costEvidence.source_commit,source:costEvidence.source_reference,source_url:costEvidence.source_url,required_inputs:record(costEvidence.model_metadata).input_requirements,raw_sizing_description:record(record(costEvidence.model_metadata).raw).units,converted_inputs:costEvidence.model_inputs,conversion:costEvidence.unit_conversion,secondary_input:costEvidence.second_input_conversion,derivation:record(row.parsed_source).sizing,equation:costEvidence.equation_family,coefficients:costEvidence.coefficients,limits:record(costEvidence.model_metadata).capacity_limits,original_cost:costEvidence.original_cost,source_year:costEvidence.original_cost_year,scope:row.cost_scope,escalation:costEvidence.cost_translation,material:costEvidence.material_adjustment,quantity:row.quantity,final_amount:row.amount,warnings:row.issues},null,2):undefined,provenance:lineage,originalCost:costEvidence.original_cost!=null?String(costEvidence.original_cost)+' USD ('+String(costEvidence.original_cost_year)+')':undefined,purchaseCost:money(purchase),installationCost:money(installation),costCurrency:String(record(record(row.calculation).estimate).currency??''),costPeriod:String(record(record(row.calculation).estimate).period??record(row.reference_cost).price_period??''),knownCost:capital&&cost!=null?Number(cost):purchase==null?undefined:Number(purchase)+Number(installation??0),installationPending:purchase!=null&&installation==null,cost:row.cost_status==='alias_reference'&&cost==null?'Reference pending · +0 additional':cost!==null&&cost!==undefined&&String(cost).trim()!==''&&Number.isFinite(Number(cost))?(row.cost_status==='alias_reference'?'Reference · ':'')+Number(cost).toLocaleString('en-GB',{maximumFractionDigits:2})+(row.cost_status==='alias_reference'?' · +0 additional':''):purchase!=null?money(purchase)+' + installation pending':'Unpriced',status:row.curve_id==='manual:user-price'&&purchase!=null&&Number.isFinite(Number(purchase))?'user_priced':String(row.pricing_status??row.status??'needs_review'),model:row.cost_status==='alias_reference'?'Alias → '+String(record(row.reference_cost).equipment_tag):String(row.curve_id??mapping?.curve_id??(concept.match_status==='matched'?'Matched family: '+familyNames+' · configuration pending':'No matched correlation')),range:record(row.equipment_cost_range).low_cost!==undefined?`${Number(record(row.equipment_cost_range).low_cost).toLocaleString('en-GB',{maximumFractionDigits:2})} – ${Number(record(row.equipment_cost_range).high_cost).toLocaleString('en-GB',{maximumFractionDigits:2})}`:undefined,blocker:rows(record(row.decision).blockers).length?'Review sizing':String(record(row.decision).next_action??'').replaceAll('_',' '),match:String(record(row.decision).matching??''),candidates:Array.isArray(record(row.decision).candidate_curve_ids)?(record(row.decision).candidate_curve_ids as unknown[]).map(String).join(', '):'',rationale:String(record(record(row.decision).conceptual_matching).reason??record(row.parsed_source).rationale??mapping?.rationale??'No documented model-selection rationale')};
  });
}
