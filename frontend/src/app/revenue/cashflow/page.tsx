import {redirect} from 'next/navigation';
export default async function LegacyCashflow({searchParams}:{searchParams:Promise<Record<string,string|string[]|undefined>>}){
 const params=new URLSearchParams();
 for(const [key,value] of Object.entries(await searchParams)){
  if(Array.isArray(value))for(const item of value)params.append(key,item);
  else if(value!==undefined)params.set(key,value);
 }
 redirect('/cashflow'+(params.size?'?'+params.toString():''));
}
