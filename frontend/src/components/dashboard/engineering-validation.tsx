"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/client-api";
import { apiError } from "@/lib/assessment";
import { Button } from "@/components/ui/button";
type Report = {
  version: string;
  checked_at: string;
  passed: boolean;
  passed_cases: number;
  total_cases: number;
  limitations: string[];
  cases: {
    id: string;
    label: string;
    basis: string;
    passed: boolean;
    metrics: {
      metric: string;
      expected: number;
      actual: number | null;
      passed: boolean;
    }[];
  }[];
};
export function EngineeringValidation() {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    apiFetch("/api/engineering/validation", { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) throw Error(await apiError(r));
        return r.json();
      })
      .then((data: Report) => {
        if (!controller.signal.aborted) setReport(data);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false);
      });
    return () => controller.abort();
  }, [revision]);
  function load() {
    setBusy(true);
    setError("");
    setRevision((v) => v + 1);
  }
  function download() {
    if (!report) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "flowvalue-engineering-reference-checks.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <section
      className="panel extension-panel"
      aria-label="Engineering reference checks"
    >
      <h2>Engineering reference checks</h2>
      <p>
        {report
          ? `${report.passed_cases}/${report.total_cases} documented reference cases pass · ${report.version}`
          : "Loading deterministic reference checks…"}{" "}
        No AI requests are used.
      </p>
      <p>
        These checks verify implementation consistency. They do not establish
        that a project is complete, independently validated or code compliant.
      </p>
      <div className="extension-actions">
        <Button variant="outline" disabled={busy} onClick={load}>
          {busy ? "Checking…" : "Refresh reference checks"}
        </Button>
        <Button variant="outline" disabled={!report || busy} onClick={download}>
          Download validation record
        </Button>
      </div>
      {error && <p role="alert">{error}</p>}
      {report?.passed === false && (
        <p role="alert" className="engineering-warning">
          A reference regression was detected. Resolve it before relying on
          calculations.
        </p>
      )}
      {report && (
        <details>
          <summary>Inspect checks and limitations</summary>
          <p>Checked {new Date(report.checked_at).toLocaleString()}</p>
          {report.cases.map((c) => (
            <details key={c.id}>
              <summary>
                {c.passed ? "Pass" : "FAIL"} · {c.label}
              </summary>
              <p>{c.basis}</p>
              <table>
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Reference</th>
                    <th>Computed</th>
                  </tr>
                </thead>
                <tbody>
                  {c.metrics.map((m) => (
                    <tr key={m.metric}>
                      <td>{m.metric.replaceAll("_", " ")}</td>
                      <td>{m.expected.toPrecision(8)}</td>
                      <td>
                        {m.actual === null
                          ? "Not defined"
                          : m.actual.toPrecision(8)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          ))}
          {report.limitations.map((n) => (
            <p key={n}>{n}</p>
          ))}
        </details>
      )}
    </section>
  );
}
