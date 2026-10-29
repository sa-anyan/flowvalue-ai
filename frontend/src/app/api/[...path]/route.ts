import { NextRequest } from "next/server";

const paths = new Set([
  "api/equipment/catalog",
  "api/equipment/match",
  "api/equipment/interpret",
  "health",
  "api/config",
  "api/projects",
  "api/projects/validate-reference",
  "api/streams/parse/dwxml",
  "api/streams/parse/excel",
  "api/process-description/check",
  "api/process-description/review",
  "api/assessment/tornado",
  "api/copilot/executive-memo",
  "api/copilot/status",
  "api/copilot/check",
  "api/indices/cepci",
  "api/policy/screen",
  "api/release/check",
  "api/study/review",
  "api/study/apply-opex",
  "api/integrations/catalog",
  "api/engineering/validation",
  "api/engineering/investigate",
  "api/engineering/research",
  "api/engineering/apply-baseline",
  "api/engineering/reviews/identity",
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
  if (
    !paths.has(target) &&
    !/^api\/projects\/[0-9a-f-]{36}$/i.test(target) &&
    !/^api\/engineering\/reviews\/[0-9a-f-]{36}(?:\/(?:events|access|revoke))?$/i.test(
      target,
    )
  )
    return Response.json({ detail: "Unknown API route" }, { status: 404 });
  try {
    let engineeringBody: Uint8Array | undefined;
    if (
      request.method === "POST" &&
      [
        "api/streams/parse/excel",
        "api/process-description/check",
        "api/process-description/review",
        "api/equipment/match",
        "api/equipment/interpret",
      ].includes(target)
    ) {
      const limit = target.endsWith("/excel")
        ? 4 * 1024 * 1024 + 65536
        : 3 * 1024 * 1024;
      if (Number(request.headers.get("content-length")) > limit)
        return Response.json(
          { detail: "Engineering request exceeds upload/body limit." },
          { status: 413 },
        );
      const reader = request.body?.getReader();
      const chunks: Uint8Array[] = [];
      let length = 0;
      if (reader) {
        while (true) {
          const chunk = await reader.read();
          if (chunk.done) break;
          length += chunk.value.byteLength;
          if (length > limit) {
            await reader.cancel();
            return Response.json(
              { detail: "Engineering request exceeds upload/body limit." },
              { status: 413 },
            );
          }
          chunks.push(chunk.value);
        }
      }
      engineeringBody = new Uint8Array(length);
      let offset = 0;
      for (const chunk of chunks) {
        engineeringBody.set(chunk, offset);
        offset += chunk.byteLength;
      }
    }
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
          request.method === "GET"
            ? undefined
            : engineeringBody
              ? new Blob([engineeringBody as BlobPart])
              : await request.arrayBuffer(),
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
