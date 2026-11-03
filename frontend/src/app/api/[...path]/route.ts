import {MAX_UPLOAD_REQUEST_BYTES} from '../../../lib/upload-limits';
import {NextResponse,type NextRequest} from 'next/server';
import {cloudAuthEnabled,requestSession,setSession} from '../../../lib/cloud-auth';
async function proxy(request: NextRequest, context: {params: Promise<{path: string[]}>}) {
  const origin=request.headers.get('origin');
  if (origin && origin !== request.nextUrl.origin)
    return Response.json({detail:'Cross-origin assessment requests are not allowed'},{status:403});
  const {path} = await context.params;
  if (!['assessments','versions','catalogue','health','currency'].includes(path[0]) || path.some(p => !/^[a-zA-Z0-9_-]+$/.test(p)))
    return Response.json({detail: 'Unknown endpoint'}, {status:404});
  const limit=request.method==='POST'&&path.length===1&&path[0]==='assessments'?MAX_UPLOAD_REQUEST_BYTES:5*1024*1024;
  const declared=Number(request.headers.get('content-length'));
  if(Number.isFinite(declared)&&declared>limit)return Response.json({detail:'Request too large; workbooks support up to 20 MiB'}, {status:413});
  const body = ['GET','HEAD'].includes(request.method) ? undefined : await request.arrayBuffer();
  if (body && body.byteLength > limit) return Response.json({detail:'Request too large'}, {status:413});
  try {
    const session=cloudAuthEnabled()?await requestSession(request):{access:'',renewed:null};
    if(cloudAuthEnabled()&&!session.access&&path[0]!=='health')return NextResponse.json({detail:'Sign in required'},{status:401});
    const response = await fetch(`${process.env.FLOWVALUE_BACKEND_URL || 'http://127.0.0.1:8000'}/api/${path.join('/')}${request.nextUrl.search}`, {
      method:request.method, body, headers: {'Content-Type':request.headers.get('content-type') || 'application/json',...(session.access?{Authorization:'Bearer '+session.access}:{})},
      cache:'no-store', signal:AbortSignal.timeout(path.includes('monte-carlo')&&path.at(-1)==='export'?120000:15000), redirect:'error'
    });
    const outgoing = new NextResponse(response.body,{status:response.status, headers:{'Content-Type':response.headers.get('content-type') || 'application/json','Cache-Control':'no-store',...(response.headers.get('content-disposition')?{'Content-Disposition':response.headers.get('content-disposition')!}:{})}});
    return session.renewed?setSession(outgoing,session.renewed):outgoing;
  } catch {return Response.json({detail:'Assessment backend unavailable. Please retry shortly.'},{status:503});}
}
export {proxy as GET,proxy as POST,proxy as PATCH};
