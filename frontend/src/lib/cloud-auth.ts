import type {NextRequest} from 'next/server';
import {NextResponse} from 'next/server';
export const cloudAuthEnabled=()=>process.env.FLOWVALUE_CLOUD==='true';
const endpoint=()=>`${process.env.SUPABASE_URL}/auth/v1/token`;
export async function tokenRequest(grant:string,body:object){
 const response=await fetch(endpoint()+`?grant_type=${grant}`,{method:'POST',headers:{apikey:process.env.SUPABASE_PUBLISHABLE_KEY||'','Content-Type':'application/json'},body:JSON.stringify(body),cache:'no-store',redirect:'error',signal:AbortSignal.timeout(10000)});
 if(!response.ok)return null;return response.json();
}
export type Session={access_token:string;refresh_token:string;expires_in:number};
export function setSession(response:NextResponse,session:Session){
 const settings={httpOnly:true,secure:process.env.NODE_ENV==='production',sameSite:'lax' as const,path:'/'};
 response.cookies.set('fv_access',session.access_token,{...settings,maxAge:Math.max(1,session.expires_in-60)});
 response.cookies.set('fv_refresh',session.refresh_token,{...settings,maxAge:30*86400});return response;
}
export async function requestSession(request:NextRequest):Promise<{access:string;renewed:Session|null}>{
 let access=request.cookies.get('fv_access')?.value||'';let expiry=0;
 try{expiry=JSON.parse(Buffer.from(access.split('.')[1],'base64url').toString()).exp||0;}catch{}
 // exp is a refresh scheduling hint only; backend verifies every access token.
 if(expiry<Date.now()/1000+1800){
  const refresh=request.cookies.get('fv_refresh')?.value;
  if(refresh){const renewed=await tokenRequest('refresh_token',{refresh_token:refresh});if(renewed){return {access:renewed.access_token,renewed};}}
 }
 return {access,renewed:null};
}
