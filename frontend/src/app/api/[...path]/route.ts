import {NextResponse,type NextRequest} from 'next/server';
import {cloudAuthEnabled,requestSession,setSession} from '../../../lib/cloud-auth';
async function proxy(request: NextRequest, context: {params: Promise<{path: string[]}>}) {
  const origin=request.headers.get('origin');
  if (origin && origin !== request.nextUrl.origin)
    return Response.json({detail:'Cross-origin assessment requests are not allowed'},{status:403});
  const {path} = await context.params;
  if (!['assessments','versions','catalogue','health'].includes(path[0]) || path.some(p => !/^[a-zA-Z0-9_-]+$/.test(p)))
    return Response.json({detail: 'Unknown endpoint'}, {status:404});
  const body = ['GET','HEAD'].includes(request.method) ? undefined : await request.arrayBuffer();
  if (body && body.byteLength > 5 * 1024 * 1024) return Response.json({detail:'Request too large'}, {status:413});
  try {
    const session=cloudAuthEnabled()?await requestSession(request):{access:'',renewed:null};
    if(cloudAuthEnabled()&&!session.access&&path[0]!=='health')return NextResponse.json({detail:'Sign in required'},{status:401});
    const response = await fetch(`${process.env.FLOWVALUE_BACKEND_URL || 'http://127.0.0.1:8000'}/api/${path.join('/')}`, {
      method:request.method, body, headers: {'Content-Type':request.headers.get('content-type') || 'application/json',...(session.access?{Authorization:'Bearer '+session.access}:{})},
      cache:'no-store', signal:AbortSignal.timeout(15000), redirect:'error'
    });
    const outgoing = new NextResponse(response.body,{status:response.status, headers:{'Content-Type':response.headers.get('content-type') || 'application/json','Cache-Control':'no-store'}});
    return session.renewed?setSession(outgoing,session.renewed):outgoing;
  } catch {return Response.json({detail:'Assessment backend unavailable. Please retry shortly.'},{status:503});}
}
export {proxy as GET,proxy as POST,proxy as PATCH};
