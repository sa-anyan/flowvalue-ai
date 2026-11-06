/** Display adapters for saved Python outputs. Missing records remain missing. */
type Row=Record<string,unknown>;
export type RevenueSeries={id:string;name:string;colour:string;values:(number|null)[]};
export const streamColours=['#007f86','#7354ba','#b25f00','#3277b6','#aa4674','#547e22','#886337','#496b91'];
export function streamColour(id:string){let hash=0;for(const c of id)hash=(hash*31+c.charCodeAt(0))>>>0;return streamColours[hash%streamColours.length];}
export function streamPalette(ids:string[]){
 const assigned=new Map<string,string>(),used=new Set<string>();
 for(const id of [...new Set(ids)].sort()){
  let colour=streamColour(id);
  if(used.has(colour))colour=streamColours.find(c=>!used.has(c))??colour;
  used.add(colour);assigned.set(id,colour);
 }
 return assigned;
}
const rows=(v:unknown):Row[]=>Array.isArray(v)?v as Row[]:[];
const numeric=(v:unknown)=>v===null||v===undefined||v===''||!Number.isFinite(Number(v))?null:Number(v);
export function revenueSeries(config:Row,result:Row){
 const annual=rows(result.annual).slice().sort((a,b)=>Number(a.year)-Number(b.year));
 const years=annual.map(a=>String(a.year));
 const names=new Map([...rows(config.sales),...rows(config.commercial_lines)].map(l=>[String(l.id),String(l.name??l.id)]));
 const records=[...rows(result.products).map(p=>({id:'product:'+p.product_id,key:String(p.product_id),year:String(p.year),value:numeric(p.net_sales_revenue)})),...rows(result.commercial).map(p=>({id:'commercial:'+p.line_id,key:String(p.line_id),year:String(p.year),value:numeric(p.revenue)}))];
 const palette=streamPalette(records.map(p=>p.id));
 const streams:RevenueSeries[]=[...new Set(records.map(p=>p.id))].map(id=>{
  const group=records.filter(p=>p.id===id);
  return {id,name:names.get(group[0].key)??group[0].key,colour:palette.get(id)!,values:years.map(year=>{const found=group.filter(p=>p.year===year);return !found.length||found.some(p=>p.value===null)?null:found.reduce((s,p)=>s+p.value!,0);})};
 });
 const total:RevenueSeries={id:'total',name:'Total revenue',colour:'#173c49',values:annual.map(a=>numeric(a.sales_revenue))};
 return {years,streams,total};
}
export function selectedSubtotal(streams:RevenueSeries[],years:string[]):RevenueSeries{
 return {id:'subtotal',name:'Selected subtotal',colour:'#8b5a00',values:years.map((_,i)=>!streams.length||streams.some(s=>s.values[i]===null)?null:streams.reduce((sum,s)=>sum+s.values[i]!,0))};
}
