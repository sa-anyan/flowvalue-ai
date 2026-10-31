import type {NextRequest} from 'next/server';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
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
    const response = await fetch(`${process.env.FLOWVALUE_BACKEND_URL || 'http://127.0.0.1:8000'}/api/${path.join('/')}`, {
      method:request.method, body, headers: {'Content-Type':request.headers.get('content-type') || 'application/json'},
      cache:'no-store', signal:AbortSignal.timeout(15000), redirect:'error'
    });
    return new Response(response.body,{status:response.status, headers:{'Content-Type':response.headers.get('content-type') || 'application/json','Cache-Control':'no-store'}});
  } catch {return Response.json({detail:'Local backend unavailable. Start the assessment API on port 8000.'},{status:503});}
}
export {proxy as GET,proxy as POST,proxy as PATCH};
