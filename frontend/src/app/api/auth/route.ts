import {NextRequest,NextResponse} from 'next/server';
import {cloudAuthEnabled,setSession,tokenRequest} from '../../../lib/cloud-auth';
export async function POST(request:NextRequest){
 if(request.headers.get('origin')!==request.nextUrl.origin)return NextResponse.json({detail:'Same-origin sign-in required'},{status:403});
 if(!cloudAuthEnabled())return NextResponse.json({ok:true});
 const {email,password,action}=await request.json();
 if(action==='logout'){
  const response=NextResponse.json({ok:true});response.cookies.delete('fv_access');response.cookies.delete('fv_refresh');return response;
 }
 if(typeof email!=='string'||typeof password!=='string'||email.length>320||password.length>4096)return NextResponse.json({detail:'Enter your email and password'},{status:400});
 try{
  const session=await tokenRequest('password',{email,password});
  if(!session)return NextResponse.json({detail:'Sign-in failed. Check your account details and email confirmation.'},{status:401});
  return setSession(NextResponse.json({ok:true}),session);
 }catch{return NextResponse.json({detail:'Account service is temporarily unavailable'},{status:503});}
}
