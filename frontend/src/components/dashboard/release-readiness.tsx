"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/client-api";
import { apiError, type AssessmentRequest } from "@/lib/assessment";

type Report = {
  checked_at: string;
  checks: { label: string; status: string; detail: string }[];
  notice: string;
};
export function ReleaseReadiness({ project }: { project: AssessmentRequest }) {
  const signature = JSON.stringify(project);
  const [result, setResult] = useState<{
    signature: string;
    report: Report;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run() {
    setBusy(true);
    setError("");
    try {
      const r = await apiFetch("/api/release/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: signature,
      });
      if (!r.ok) throw Error(await apiError(r));
      setResult({ signature, report: await r.json() });
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Release check unavailable; retry.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel extension-panel">
      <h2>Release & project readiness</h2>
      <p>
        Run deterministic API, engineering and export checks for this scenario.
        No paid AI calls. Account ownership and save/reload acceptance require a
        separate signed-in browser test.
      </p>
      <Button onClick={run} disabled={busy}>
        {busy ? "Checking…" : "Run readiness checks"}
      </Button>
      <p role="status">{error}</p>
      {result && (
        <>
          <p>
            {result.signature !== signature
              ? "Project changed — results are stale. Run checks again."
              : `Checked ${result.report.checked_at}`}
          </p>
          <ul>
            {result.report.checks.map((c) => (
              <li key={c.label}>
                <strong>
                  {c.status.toUpperCase()} · {c.label}
                </strong>
                : {c.detail}
              </li>
            ))}
          </ul>
          <p>{result.report.notice}</p>
        </>
      )}
    </section>
  );
}
