"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/client-api";
import { apiError } from "@/lib/assessment";
import { Button } from "@/components/ui/button";

export type AIStatus = {
  state: "configured" | "disabled" | "not_configured";
  can_generate: boolean;
  model: string;
  connection_verified: boolean;
  research_domains: string[];
  message: string;
};

export function useAIStatus(authRevision: number) {
  const [status, setStatus] = useState<AIStatus | null>(null);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const refresh = useCallback(() => setRevision((v) => v + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    apiFetch("/api/copilot/status", { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) throw Error(await apiError(r));
        return r.json();
      })
      .then((data: AIStatus) => {
        if (controller.signal.aborted) return;
        setStatus(data);
        setError("");
      })
      .catch((e) => {
        if (!controller.signal.aborted) {
          setStatus(null);
          setError(e.message);
        }
      });
    return () => controller.abort();
  }, [authRevision, revision]);
  return { status, error, refresh };
}

export function AIConnection({
  status,
  error,
  refresh,
}: ReturnType<typeof useAIStatus>) {
  const [checking, setChecking] = useState(false);
  const [diagnostic, setDiagnostic] = useState("");
  async function check() {
    setChecking(true);
    setDiagnostic("");
    try {
      const r = await apiFetch("/api/copilot/check", { method: "POST" });
      if (!r.ok) throw Error(await apiError(r));
      const data: AIStatus = await r.json();
      setDiagnostic(data.message);
    } catch (e) {
      setDiagnostic(e instanceof Error ? e.message : "Connection check failed");
    } finally {
      setChecking(false);
    }
  }
  return (
    <section className="panel extension-panel" aria-label="AI connection">
      <div className="panel-heading">
        <div>
          <h2>AI connection</h2>
          <p>{error || status?.message || "Checking AI availability…"}</p>
          {status?.can_generate && (
            <small>Configured model: {status.model}</small>
          )}
        </div>
        <div className="extension-actions">
          <Button
            variant="outline"
            onClick={() => {
              setDiagnostic("");
              refresh();
            }}
          >
            Refresh AI status
          </Button>
          <Button disabled={!status?.can_generate || checking} onClick={check}>
            {checking ? "Checking connection…" : "Check AI connection"}
          </Button>
        </div>
      </div>
      {diagnostic && <p role="status">{diagnostic}</p>}
      <details>
        <summary>AI data use & configuration</summary>
        <p>
          Research sends the computed cost profile, your question and optional
          market context to OpenAI and uses live web search. Memos send project
          context, calculated economics, equipment costs and sensitivities.
          Original simulation files and authentication tokens are not sent.
          Responses are requested with storage disabled; provider data policies
          still apply.
        </p>
        <p>
          Research includes linked sources where evidence is established.
          Executive memos use computed scenario data and do not perform market
          research. Both require human review. AI never changes assumptions
          automatically.
        </p>
        <p>
          Workspace administrators configure the provider key on the server.
          Keys are never entered or displayed in this dashboard. After
          configuration changes, refresh AI status and run a connection check.
        </p>
      </details>
    </section>
  );
}
