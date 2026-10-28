"use client";
import { useRef, useState, useEffect } from "react";
import { Upload, LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/client-api";
import { apiError } from "@/lib/assessment";
import {
  descriptionIsCurrent,
  emptyDescription,
  type BalanceAttachment,
  type BalanceEvidence,
  type BalanceIssue,
} from "@/lib/balance";

export function BalanceImport({
  value,
  onChange,
}: {
  value: BalanceAttachment | null;
  onChange: (value: BalanceAttachment) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const current = useRef(value);
  useEffect(() => {
    current.current = value;
  }, [value]);
  const [busy, setBusy] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [draft, setDraft] = useState("");
  const [shown, setShown] = useState(50);
  const description = value?.description.text ?? draft;
  async function upload(file: File) {
    if (busy) return;
    setError("");
    if (!/\.(xlsx|xls)$/i.test(file.name) || file.size > 4 * 1024 * 1024) {
      setError("Choose an .xlsx or .xls workbook, up to 4 MiB.");
      return;
    }
    setBusy("parse");
    setStatus(`Uploading and parsing ${file.name}…`);
    try {
      const body = new FormData();
      body.append("file", file);
      const response = await apiFetch("/api/streams/parse/excel", {
        method: "POST",
        body,
      });
      if (!response.ok) throw Error(await apiError(response));
      const report = await response.json();
      onChange({
        report,
        description: { ...emptyDescription, text: description },
      });
      setShown(50);
      setStatus(
        `Parsing finished with ${report.issues.length} issues for review. ${report.tables.length} tables detected across ${report.sheets.length} worksheets. Coverage is partial.`,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Workbook parsing failed");
      setStatus("Parsing failed. The previous import, if any, is retained.");
    } finally {
      setBusy("");
      if (input.current) input.current.value = "";
    }
  }
  async function review(ai: boolean) {
    if (!value || busy || !description.trim()) return;
    const snapshot = value;
    setBusy("review");
    setError("");
    try {
      const r = await apiFetch(
        `/api/process-description/${ai ? "review" : "check"}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ report: snapshot.report, description }),
        },
      );
      if (!r.ok) throw Error(await apiError(r));
      const result = await r.json();
      if (
        current.current?.report.sha256 !== snapshot.report.sha256 ||
        current.current?.description.text !== description
      ) {
        setStatus("Inputs changed during review. Run the comparison again.");
        return;
      }
      onChange({ ...snapshot, description: result });
      setStatus(
        ai
          ? "AI mapping compared with workbook connections. Review the findings below."
          : "Basic tag check complete. AI semantic mapping has not run.",
      );
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Description comparison failed",
      );
    } finally {
      setBusy("");
    }
  }
  function download() {
    if (!value) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = `${value.report.filename}.parsed.json`;
    link.click();
    URL.revokeObjectURL(url);
  }
  const report = value?.report;
  const sources = new Map<string, BalanceEvidence>();
  for (const e of report?.entities ?? [])
    for (const v of [e.id_evidence, ...e.values]) sources.set(v.id, v);
  for (const v of report?.declarations ?? []) sources.set(v.id, v);
  function source(ids: string[]) {
    return ids
      .map((id) => sources.get(id))
      .filter((v): v is BalanceEvidence => !!v)
      .map((v) => `${v.sheet}!${v.cell}`)
      .join(", ");
  }
  function issues(items: BalanceIssue[]) {
    return items.slice(0, 100).map((item, i) => (
      <li key={i}>
        <span className={`balance-status ${item.status}`}>{item.status}</span>{" "}
        {item.message}
        {item.evidence_ids.length > 0 && (
          <small>{source(item.evidence_ids)}</small>
        )}
      </li>
    ));
  }
  return (
    <section
      className="panel balance-import"
      id="engineering-balance"
      aria-label="Excel mass and energy balance"
    >
      <div className="panel-heading">
        <div>
          <h2>Mass &amp; energy balance</h2>
          <p>
            Read engineering workbooks with source cells, explicit units and
            transparent gaps.
          </p>
        </div>
        {report && <Button onClick={download}>Download parsed evidence</Button>}
      </div>
      <div className="balance-entry-grid">
        <div>
          <input
            ref={input}
            type="file"
            accept=".xlsx,.xls"
            className="sr-only"
            aria-label="Upload Excel mass and energy balance"
            onChange={(e) => {
              if (e.target.files?.[0]) void upload(e.target.files[0]);
            }}
          />
          <button
            className="dropzone"
            disabled={!!busy}
            onClick={() => input.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (e.dataTransfer.files[0]) void upload(e.dataTransfer.files[0]);
            }}
          >
            {busy === "parse" ? (
              <LoaderCircle className="spin" size={22} />
            ) : (
              <Upload size={22} />
            )}
            <strong>
              {busy === "parse"
                ? "Parsing workbook…"
                : report?.filename || "Upload an Excel mass & energy balance"}
            </strong>
            <span>.xlsx or .xls · up to 4 MiB</span>
          </button>
          <p className="upload-message">
            Excel imports stay separate from economic assumptions and equipment
            costing. Parsed evidence is retained in this browser tab and can be
            downloaded.
          </p>
        </div>
        <div className="balance-dialogue">
          <label htmlFor="process-description">
            <strong>Describe your process</strong>
          </label>
          <textarea
            id="process-description"
            maxLength={6000}
            rows={4}
            placeholder="Explain the process sequence, equipment names or workbook ambiguities…"
            value={description}
            disabled={busy === "parse"}
            onChange={(e) => {
              setDraft(e.target.value);
              if (value)
                onChange({
                  ...value,
                  description: { ...value.description, text: e.target.value },
                });
            }}
          />
          <div className="extension-actions">
            <Button
              disabled={!report || !description.trim() || !!busy}
              onClick={() => review(true)}
            >
              {busy === "review" ? "Comparing…" : "Compare with AI"}
            </Button>
            <Button
              disabled={!report || !description.trim() || !!busy}
              onClick={() => review(false)}
            >
              Basic tag check
            </Button>
          </div>
          <small>
            AI review sends this description and extracted equipment names, tags
            and endpoints to the configured AI provider. It runs only on click;
            no web research. Numerical balances remain deterministic.
          </small>
          {value?.description.reviewed_at && !descriptionIsCurrent(value) && (
            <p role="status">
              Description changed. Previous comparison is stale; compare again.
            </p>
          )}
          {value && descriptionIsCurrent(value) && (
            <details open>
              <summary>
                Clarifications &amp; comparison{" "}
                {value.description.model
                  ? `· ${value.description.model}`
                  : "· basic check"}
              </summary>
              <ul className="balance-issues">
                {issues(value.description.findings)}
              </ul>
              {value.description.questions.map((q, i) => (
                <p key={i}>{q}</p>
              ))}
            </details>
          )}
        </div>
      </div>
      <p role="status">
        {status ||
          (report
            ? `Parsed ${report.filename}: ${report.tables.length} tables across ${report.sheets.length} worksheets; ${report.issues.length} issues for review. Coverage is partial.`
            : "No engineering workbook uploaded.")}
      </p>
      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}
      {report && (
        <>
          <div className="balance-counts">
            {["material", "energy", "equipment"].map((kind) => (
              <span key={kind}>
                <strong>
                  {report.entities.filter((e) => e.kind === kind).length}
                </strong>{" "}
                {kind === "material"
                  ? "material stream records"
                  : kind === "energy"
                    ? "energy stream records"
                    : "equipment records"}
              </span>
            ))}
          </div>
          <p>{report.coverage}</p>
          <details>
            <summary>Worksheets &amp; detected tables</summary>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Worksheet</th>
                    <th>Extent</th>
                    <th>Tables</th>
                    <th>Extracted / nonempty cells</th>
                  </tr>
                </thead>
                <tbody>
                  {report.sheets.map((s) => (
                    <tr key={s.name}>
                      <td>
                        {s.name}
                        {s.hidden ? " (hidden)" : ""}
                      </td>
                      <td>
                        {s.rows} × {s.columns}
                      </td>
                      <td>{s.tables}</td>
                      <td>
                        {s.extracted_cells} / {s.nonempty_cells}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {report.tables.map((t) => (
              <p key={t.id}>
                {t.sheet}!{t.range} · {t.kind} ·{" "}
                {t.orientation.replaceAll("_", " ")} · {t.status}
              </p>
            ))}
          </details>
          <details open>
            <summary>
              Engineering validation ·{" "}
              {report.checks.filter((c) => c.status === "verified").length}{" "}
              checks verified in declared scope
            </summary>
            <p>
              Verified denotes source-supported observations or the named
              arithmetic check. It does not certify the plant or complete
              workbook.
            </p>
            <ul className="balance-issues">
              {report.checks.slice(0, 100).map((c, i) => (
                <li key={i}>
                  <span className={`balance-status ${c.status}`}>
                    {c.status}
                  </span>{" "}
                  <strong>
                    {c.name} · {c.scope}
                  </strong>
                  <p>
                    {c.message}
                    {c.residual !== null
                      ? ` Residual: ${c.residual.toPrecision(6)} ${c.unit}.`
                      : ""}
                  </p>
                  <small>{source(c.evidence_ids)}</small>
                </li>
              ))}
            </ul>
          </details>
          <details>
            <summary>
              Issues &amp; missing information · {report.issues.length}
            </summary>
            <ul className="balance-issues">{issues(report.issues)}</ul>
            {report.issues.length > 100 && (
              <p>First 100 shown. Download parsed evidence for every issue.</p>
            )}
          </details>
          <details>
            <summary>
              Extracted streams, equipment &amp; cell evidence ·{" "}
              {report.entities.length} records
            </summary>
            {report.entities.slice(0, shown).map((e) => (
              <details key={e.key} className="balance-record">
                <summary>
                  {e.identifier} {e.case ? `· ${e.case}` : ""} · {e.kind} ·{" "}
                  {e.status}
                </summary>
                <p>
                  Identifier source: {e.id_evidence.sheet}!{e.id_evidence.cell}.{" "}
                  {e.id_evidence.note}
                </p>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Property</th>
                        <th>Original</th>
                        <th>Normalized</th>
                        <th>Source</th>
                        <th>Status / interpretation</th>
                      </tr>
                    </thead>
                    <tbody>
                      {e.values.map((v) => (
                        <tr key={v.id}>
                          <td>
                            {v.label}
                            {v.component ? ` · ${v.component}` : ""}
                          </td>
                          <td>
                            {String(v.original_value ?? "Missing")}{" "}
                            {v.original_unit}
                          </td>
                          <td>
                            {String(v.normalized_value ?? "Unresolved")}{" "}
                            {v.normalized_unit}
                          </td>
                          <td>
                            {v.sheet}!{v.cell}
                            <small>Header: {v.header_cells.join(", ")}</small>
                            {v.formula && <code>{v.formula}</code>}
                          </td>
                          <td>
                            <span className={`balance-status ${v.status}`}>
                              {v.status}
                            </span>
                            <small>{v.note}</small>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            ))}
            {shown < report.entities.length && (
              <Button onClick={() => setShown(shown + 50)}>
                Show 50 more records
              </Button>
            )}
          </details>
          <details>
            <summary>Limits &amp; source fingerprint</summary>
            {report.limitations.map((l) => (
              <p key={l}>{l}</p>
            ))}
            <p className="balance-fingerprint">
              SHA-256 {report.sha256} · Parser {report.parser_version}
            </p>
            {report.declarations.map((v) => (
              <p key={v.id}>
                {v.label}: {String(v.original_value)} · {v.sheet}!{v.cell} ·{" "}
                {v.status}
              </p>
            ))}
          </details>
        </>
      )}
    </section>
  );
}
