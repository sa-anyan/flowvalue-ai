import { NextRequest } from "next/server";

const paths = new Set([
  "health",
  "api/config",
  "api/projects",
  "api/streams/parse/dwxml",
  "api/assessment/tornado",
  "api/copilot/executive-memo",
  "api/copilot/status",
  "api/copilot/check",
  "api/indices/cepci",
  "api/integrations/catalog",
  "api/engineering/validation",
  "api/integrations/openpytea/equipment",
  "api/integrations/biosteam/import",
  "api/demo",
  "api/assessment",
  "api/assessment/universal-suggestions",
  "api/copilot/research-sensitivities",
  "api/costing/bom",
  "api/financial/dcf",
  "api/financial/monte-carlo",
  "api/streams/parse/json",
  "api/streams/parse/csv",
  "api/export/excel",
  "api/export/pdf",
]);

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const target = `api/${path.join("/")}`;
  if (!paths.has(target) && !/^api\/projects\/[0-9a-f-]{36}$/i.test(target))
    return Response.json({ detail: "Unknown API route" }, { status: 404 });
  try {
    const upstream = await fetch(
      `${(process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "")}/${target}`,
      {
        method: request.method,
        headers: Object.fromEntries(
          ["content-type", "authorization"]
            .filter((name) => request.headers.has(name))
            .map((name) => [name, request.headers.get(name)!]),
        ),
        body:
          request.method === "GET" ? undefined : await request.arrayBuffer(),
        cache: "no-store",
        signal: AbortSignal.timeout(240000),
      },
    );
    const headers = new Headers({ "Cache-Control": "no-store" });
    for (const name of [
      "content-type",
      "content-disposition",
      "x-accel-buffering",
    ]) {
      const value = upstream.headers.get(name);
      if (value) headers.set(name, value);
    }
    return new Response(upstream.body, { status: upstream.status, headers });
  } catch {
    return Response.json(
      {
        detail:
          "The calculation service is unavailable or starting up. Wait a moment and retry; your current project has been retained.",
      },
      { status: 503 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
