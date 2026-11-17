import {list, obj, text, words, type Row} from './guided-flow';

export type CostNode = {id:string; label:string; amount:unknown; record:Row; children:CostNode[]; grain:string};
export const analystNumber=(value:unknown):number|null => (typeof value==='string'||typeof value==='number')&&String(value).trim()!==''&&Number.isFinite(Number(value))?Number(value):null;
export const exactMoney=(value:unknown) => analystNumber(value)===null?'Not established':new Intl.NumberFormat('en-GB',{minimumFractionDigits:2,maximumFractionDigits:2}).format(Math.abs(analystNumber(value)!)<0.005?0:analystNumber(value)!);
export function costReconciliation(node:CostNode) {
 const values=node.children.map(c=>analystNumber(c.amount));
 const known=values.reduce<number>((sum,v)=>sum+(v??0),0), expected=analystNumber(node.amount);
 const leaves=(node:CostNode):CostNode[]=>node.children.length?node.children.flatMap(leaves):[node];
 const unresolved=node.children.flatMap(leaves).filter(n=>analystNumber(n.amount)===null).length;
 const delta=expected===null?null:expected-known;
 return {known,expected,unresolved,delta,matches:delta!==null&&Math.abs(delta)<0.01,complete:node.children.length>0&&node.record.complete!==false&&expected!==null&&!unresolved&&delta!==null&&Math.abs(delta)<0.01};
}
export function groupCostNodes(nodes:CostNode[],by:(node:CostNode)=>string):CostNode[] {
 const groups=new Map<string,CostNode[]>();
 for(const node of nodes){const key=by(node)||'Unclassified';groups.set(key,[...(groups.get(key)||[]),node]);}
 return [...groups].map(([label,children],i)=>({id:`group:${i}:${label}`,label,amount:children.some(c=>analystNumber(c.amount)!==null)?children.reduce((s,c)=>s+(analystNumber(c.amount)??0),0):null,record:{basis:'Display subtotal of known saved lines; unresolved lines remain listed',unresolved_lines:children.filter(c=>analystNumber(c.amount)===null).length},children,grain:'Grouped saved ledger lines'}));
}
export function paretoRows(nodes:CostNode[]) {
 const eligible=nodes.every(c=>analystNumber(c.amount)===null||analystNumber(c.amount)!>=0);
 if(!eligible)return null;
 const sorted=nodes.filter(c=>analystNumber(c.amount)!==null).slice().sort((a,b)=>analystNumber(b.amount)!-analystNumber(a.amount)!);
 const total=sorted.reduce((sum,c)=>sum+analystNumber(c.amount)!,0);
 let cumulative=0;
 return sorted.map(node=>{cumulative+=analystNumber(node.amount)!;return {node,cumulative,total,share:total>0?cumulative/total:null};});
}
export function capexCostTree(result:Row,equipment:Row[]):CostNode {
 const factorById=new Map(list(result.lines).map(r=>[text(r.id),r]));
 const rows=list(result.breakdown);
 const children=rows.filter(r=>r.counted===true||r.status==='gap').map((r,i):CostNode=>{
  const category=text(r.category);
  let detail=list(r.factors).filter(f=>!['embedded','combined','excluded'].includes(text(f.status))).map((f,j):CostNode=>({id:`factor:${i}:${j}`,label:words(f.id),amount:f.amount,record:factorById.get(text(f.id))||f,children:[],grain:'Factor allowance · item quantities not supplied'}));
  if(category==='purchased_equipment'||category==='unit_capital_scope') {
   detail=equipment.filter(e=>e.cost_status!=='alias_reference'&&(category==='purchased_equipment'?e.cost_scope==='purchased_equipment':e.cost_scope==='unit_capital')).map((e,j)=>({id:`equipment:${i}:${j}`,label:text(e.equipment_tag)||`Equipment ${j+1}`,amount:category==='purchased_equipment'?e.equipment_cost:e.amount,record:e,children:[],grain:'Equipment estimate · component/fastener bill of materials not supplied'}));
  }
  return {id:`capex:${category||i}`,label:text(r.label)||words(category),amount:r.counted===true?r.amount:null,record:r,children:detail,grain:r.status==='gap'?'Unresolved scope':detail.length?'Saved cost category':'Category allowance · item quantities not supplied'};
 });
 // Legacy outputs without a declared additive breakdown can only show the three distinct investment components.
 const fallback=[['fixed_capital','Fixed capital'],['startup_expenses','Start-up'],['working_capital','Working capital']].map(([id,label])=>({id,label,amount:result[id],record:{amount:result[id],source:'Saved capital subtotal'},children:[],grain:'Subtotal · detailed additive breakdown not supplied'}));
 return {id:'capital',label:'CAPEX allocation',amount:result.total_capex,record:{model_id:result.model_id,status:result.status,complete:result.complete,period:result.period,currency:result.currency,scope_gaps:result.scope_gaps,breakdown_gaps:result.breakdown_gaps,inclusion_records:result.inclusion_records,non_additive_rows:rows.filter(r=>r.counted!==true&&r.status!=='gap')},children:rows.length?children:fallback,grain:'Saved investment · scope gaps remain explicit'};
}
export function opexCostTree(result:Row,year:string,grouping:'category'|'behavior'|'method'):CostNode {
 const annual=obj(obj(result.years)[year]);
 const lines=list(annual.lines);
 const cash=lines.filter(r=>r.accounting==='cash').map((r,i):CostNode=>({id:`opex:${i}:${text(r.id)}`,label:words(r.id||r.category)||`Cost ${i+1}`,amount:r.amount,record:r,children:[],grain:r.method==='quantity_price'?'Quantity × rate · saved annual calculation':r.method==='percentage'?'Factor allowance · no item-level take-off':'Saved operating ledger line'}));
 const amount=annual.annual_cash_opex??annual.resolved_cash_subtotal;
 return {id:`operations:${year}:${grouping}`,label:`Cash OPEX · year ${year}`,amount,record:{currency:result.currency,period:result.price_period,year,status:annual.status,snapshot_id:annual.snapshot_id,complete:annual.annual_cash_opex!=null,excluded_non_cash:lines.filter(r=>r.accounting!=='cash'),pending_items:[...list(result.pending_items),...list(obj(obj(obj(result.operating_detail).years)[year]).pending_items)],issues:annual.issues},children:groupCostNodes(cash,n=>words(n.record[grouping])||'Unclassified'),grain:annual.annual_cash_opex==null?'Known cash subtotal · incomplete costs remain unresolved':'Saved annual cash operating cost'};
}
export function revenueCostTree(result:Row,config:Row,draft=false):CostNode {
 const outputs=[...list(result.products),...list(result.commercial)];
 const assumptions=[...list(config.sales),...list(config.commercial_lines)];
 const ids=[...new Set([...assumptions.map(r=>text(r.id)),...outputs.map(r=>text(r.product_id||r.line_id))])].filter(Boolean);
 const nodes=ids.map((id,i):CostNode=>{
  const assumption=assumptions.find(r=>text(r.id)===id)||{};
  const calculated=outputs.find(r=>text(r.product_id||r.line_id)===id)||{};
  return {id:`income:${i}:${id}`,label:text(assumption.name)||id,amount:calculated.net_sales_revenue??calculated.revenue,record:{...calculated,commercial_assumptions:assumption,category:assumption.category||assumption.role||(calculated.product_id?'Product sales':'Commercial payments')},children:[],grain:'Saved income line · quantity/terms and price evidence'};
 });
 return {id:draft?'income-preview':'income',label:draft?'Draft annual income · unapproved':'Income at full operation',amount:obj(list(result.annual)[0]).sales_revenue,record:{basis:result.basis,issues:result.issues,draft,avoided_costs:config.avoided_costs,notice:'Avoided disposal costs and other OPEX adjustments are excluded from income. Public buyers/listings are not contracts.'},children:groupCostNodes(nodes,n=>words(n.record.category)),grain:draft?'Unapproved preview · baseline remains separate':'Saved 100% scheduled-operation basis'};
}
const csvCell=(value:unknown)=>{const raw=String(value??'');const safe=/^\s*[=+@\-]/.test(raw)?"'"+raw:raw;return '"'+safe.replaceAll('"','""')+'"';};
/** Export displayed records with the saved revision; this is a chart extract, not an economic workbook. */
export function analystCsv(root:CostNode,currency:string,period:string,revision:string,assessmentId='') {
 const lines=[['Path','Record ID','Saved/display amount','Currency','Period','Revision','Granularity','Project','State','Saved record (JSON)']];
 const visit=(node:CostNode,path:string[])=>{lines.push([[...path,node.label].join(' / '),node.id,analystNumber(node.amount)===null?'':String(node.amount),currency,period,revision,node.grain,assessmentId,root.record.draft===true?'Unapproved preview':'Saved calculation',JSON.stringify(node.record)]);node.children.forEach(child=>visit(child,[...path,node.label]));};
 visit(root,[]);return lines.map(row=>row.map(csvCell).join(',')).join('\r\n');
}

/** Binary area partition: every positive known node keeps its proportional area. */
export function treemapRects(nodes:CostNode[], aspectRatio=1) {
 const positive=nodes.filter(n=>(analystNumber(n.amount)??0)>0).slice().sort((a,b)=>analystNumber(b.amount)!-analystNumber(a.amount)!);
 const result:{node:CostNode;x:number;y:number;width:number;height:number}[]=[];
 const split=(items:CostNode[],x:number,y:number,width:number,height:number)=>{
  if(!items.length)return;
  if(items.length===1){result.push({node:items[0],x,y,width,height});return;}
  const total=items.reduce((s,n)=>s+analystNumber(n.amount)!,0);
  let index=1,amount=analystNumber(items[0].amount)!;
  while(index<items.length-1&&Math.abs(amount+analystNumber(items[index].amount)!-total/2)<Math.abs(amount-total/2)){amount+=analystNumber(items[index].amount)!;index++;}
  const fraction=amount/total;
  if(width*(Number.isFinite(aspectRatio)&&aspectRatio>0?aspectRatio:1)>=height){split(items.slice(0,index),x,y,width*fraction,height);split(items.slice(index),x+width*fraction,y,width*(1-fraction),height);}
  else {split(items.slice(0,index),x,y,width,height*fraction);split(items.slice(index),x,y+height*fraction,width,height*(1-fraction));}
 };
 split(positive,0,0,100,100);return result;
}

/** Respect the backend's separate monetary bases and scope subtotals for equipment. */
export function equipmentCostTree(result:Row,basis:Row):CostNode {
 const records=list(result.equipment).filter(r=>r.cost_status!=='alias_reference');
 const children=list(basis.components).map((part,i):CostNode=>{
  const scope=text(part.cost_scope),tags=new Set(Array.isArray(part.equipment_tags)?part.equipment_tags.map(String):[]);
  const detail=records.filter(r=>tags.has(text(r.equipment_tag))&&text(r.cost_scope)===scope).map((r,j):CostNode=>({id:`asset:${i}:${j}`,label:text(r.equipment_tag)||`Asset ${j+1}`,amount:scope==='purchased_equipment'?r.equipment_cost:r.amount,record:r,children:[],grain:'Equipment estimate · no component or fastener bill of materials supplied'}));
  return {id:`scope:${i}`,label:words(scope),amount:part.amount,record:part,children:detail,grain:'Source-defined equipment cost scope · counted once'};
 });
 const missing=records.filter(r=>analystNumber(r.equipment_cost)===null&&analystNumber(r.amount)===null);
 if(missing.length)children.push({id:'unpriced-assets',label:'Unpriced equipment · basis unresolved',amount:null,record:{notice:'No amount or monetary basis is assigned to these records.'},children:missing.map((r,i)=>({id:`unpriced:${i}`,label:text(r.equipment_tag)||`Unpriced asset ${i+1}`,amount:null,record:r,children:[],grain:'Unpriced equipment · not zero'})),grain:'Unpriced equipment · excluded from this priced subtotal'});
 return {id:`equipment:${text(basis.currency)}:${text(basis.period)}`,label:'Equipment cost · priced scope',amount:basis.amount,record:{currency:basis.currency,period:basis.period,complete:!missing.length,scope_notice:'This saved equipment subtotal is not whole-plant CAPEX. Other currencies and cost dates remain separate.',installation_issues:result.installation_issues,issues:result.issues},children,grain:'Saved equipment subtotal → source scope → asset → costing and sizing evidence'};
}
