"use client";
import { useRef, useState, useEffect } from "react";
import {
  importMethods,
  getImportMethod,
  acceptsBalanceWorkbook,
  readImportMethod,
  type ImportMethodId,
} from "@/lib/import-methods";
import { Upload, LoaderCircle } from "lucide-react";
import { ImportSampleGuide } from "./import-sample-guide";
import { EntryHelp } from "./entry-help";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/client-api";
import { apiError, type Stream } from "@/lib/assessment";
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
  onSimulationUpload,
  simulationStatus,
  simulationFileName,
  simulationBusy,
  simulationStreams,
}: {
  onSimulationUpload?: (file: File) => Promise<void>;
  simulationStatus?: string;
  simulationFileName?: string;
  simulationBusy?: boolean;
  simulationStreams?: Stream[];
  value: BalanceAttachment | null;
  onChange: (value: BalanceAttachment) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const current = useRef(value);
  useEffect(() => {
    current.current = value;
  }, [value]);
  const [methodId, setMethodId] = useState<ImportMethodId>(readImportMethod);
  const [lockedMethodId, setLockedMethodId] = useState<ImportMethodId | null>(() => {
    try {
      const selected = sessionStorage.getItem("flowvalue-import-method");
      const locked = sessionStorage.getItem("flowvalue-import-locked");
      return locked && locked === selected && importMethods.some((item) => item.id === locked)
        ? (locked as ImportMethodId)
        : null;
    } catch {
      return null;
    }
  });
  const method = getImportMethod(methodId);
  const isLocked = lockedMethodId === methodId;

  function lockSource() {
    setLockedMethodId(methodId);
    setError("");
    try {
      sessionStorage.setItem("flowvalue-import-method", methodId);
      sessionStorage.setItem("flowvalue-import-locked", methodId);
    } catch {}
  }

  function unlockSource() {
    setLockedMethodId(null);
    if (input.current) input.current.value = "";
    try {
      sessionStorage.removeItem("flowvalue-import-locked");
    } catch {}
  }
  const [busy, setBusy] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [draft, setDraft] = useState("");
  const description = value?.description.text ?? draft;
  async function upload(file: File) {
    if (busy || simulationBusy) return;
    if (!isLocked || method.mode === "unavailable") {
      setError("Lock in a supported import source before uploading.");
      return;
    }
    setError("");
    if (method.mode === "simulation") {
      const accepted =
        method.id === "csv"
          ? /\.csv$/i
          : method.id === "dwsim-native"
            ? /\.dwxml$/i
            : /\.json$/i;
      if (!accepted.test(file.name) || file.size > 4 * 1024 * 1024) {
        setError(
          "Choose a file matching the selected import type, up to 4 MiB.",
        );
        return;
      }
      if (!onSimulationUpload) {
        setError("This importer is unavailable in the current view.");
        return;
      }
      await onSimulationUpload(file);
      if (input.current) input.current.value = "";
      return;
    }
    if (method.mode === "excel" && /\.xlsm$/i.test(file.name)) {
      setError(".xlsm file selected. Parsing for this format is not available yet.");
      if (input.current) input.current.value = "";
      return;
    }
    if (
      !acceptsBalanceWorkbook(methodId, file.name) ||
      file.size > 4 * 1024 * 1024
    ) {
      setError(
        `Choose an .xlsx or .xls workbook/export for ${method.label}, up to 4 MiB. Native simulation files are not accepted by this Excel parser.`,
      );
      return;
    }
    setBusy("parse");
    setStatus(`Uploading and parsing ${file.name}…`);
    try {
      const body = new FormData();
      body.append("file", file);
      body.append("source", methodId === "aspen-hysys" ? "aspen-hysys" : "excel");
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
      setStatus(
        `Workbook uploaded: ${report.filename}.`,
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
          <div className="entry-inline-help">
            <h2>Mass &amp; energy balance</h2>
            <EntryHelp label="How workbook parsing works">
              Read engineering workbooks with source cells, explicit units and
              transparent gaps.
            </EntryHelp>
          </div>
        </div>
      </div>
      <div className="balance-entry-grid">
        <div>
          <div className="balance-import-method">
            <div className="entry-inline-help entry-method-title">
              <label htmlFor="balance-import-method"><strong>Select file type / import source</strong></label>
              <EntryHelp label={`Import requirements for ${method.label}`}>
                {method.help}
              </EntryHelp>
            </div>
            <select
              id="balance-import-method"
              value={methodId}
              disabled={!!busy || !!simulationBusy}
              onChange={(e) => {
                const selected = getImportMethod(e.target.value);
                setMethodId(selected.id);
                setLockedMethodId(null);
                setError("");
                setStatus("");
                if (input.current) input.current.value = "";
                try {
                  sessionStorage.removeItem("flowvalue-import-locked");
                  sessionStorage.setItem(
                    "flowvalue-import-method",
                    selected.id,
                  );
                } catch {}
              }}
            >
              {[
                "Spreadsheets & tables",
                "Process simulators",
                "Other inputs",
              ].map((group) => (
                <optgroup key={group} label={group}>
                  {importMethods
                    .filter((item) => item.group === group)
                    .map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.label}
                        {item.mode === "excel" && item.id !== "excel"
                          ? " · Excel export"
                          : item.mode === "simulation"
                            ? " · simulation importer"
                            : item.mode === "unavailable"
                              ? item.id === "manual"
                                ? " · supplementary context"
                                : " · not supported yet"
                              : ""}
                      </option>
                    ))}
                </optgroup>
              ))}
            </select>
          </div>
          <ImportSampleGuide
            key={methodId}
            methodId={methodId}
            locked={isLocked}
            onLock={lockSource}
            onUnlock={unlockSource}
          />
          <input
            ref={input}
            type="file"
            accept={
              method.mode === "simulation"
                ? method.id === "csv"
                  ? ".csv"
                  : method.id === "dwsim-native"
                    ? ".dwxml"
                    : ".json"
                : ".xlsx,.xls,.xlsm"
            }
            className="sr-only"
            disabled={!isLocked || method.mode === "unavailable"}
            aria-label={`Upload ${method.mode === "simulation" ? method.label : "Excel"} mass and energy balance`}
            onChange={(e) => {
              if (e.target.files?.[0]) void upload(e.target.files[0]);
            }}
          />
          {isLocked && method.mode !== "unavailable" ? <button
            className="dropzone"
            disabled={!!busy || !!simulationBusy}
            onClick={() => input.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (isLocked && e.dataTransfer.files[0]) void upload(e.dataTransfer.files[0]);
            }}
          >
            {busy === "parse" || simulationBusy ? (
              <LoaderCircle className="spin" size={22} />
            ) : (
              <Upload size={22} />
            )}
            <strong>
              {busy === "parse" || simulationBusy
                ? "Parsing workbook…"
                : (method.mode === "excel" ? report?.filename : null) ||
                  (method.mode === "excel"
                    ? "Select file or drop an Excel balance here"
                    : simulationFileName || `Select a ${method.label} file`)}
            </strong>
            <span>
              {method.mode === "excel"
                ? ".xlsx, .xls or .xlsm · up to 4 MiB · .xlsm parsing coming later"
                : method.mode === "simulation"
                  ? `${method.id === "csv" ? ".csv" : method.id === "dwsim-native" ? ".dwxml" : ".json"} · up to 4 MiB`
                  : "Choose another import method or follow the guidance above"}
            </span>
          </button> : (
            <div className="import-await-upload" role="status">
              {method.mode === "unavailable"
                ? "This import type is not supported for file extraction yet. You can still provide supplementary process context."
                : "Select Lock in above to enable file upload."}
            </div>
          )}
          {method.mode === "simulation" && simulationStatus && (
            <p className="upload-message" role="status">
              {simulationStatus}
            </p>
          )}
          {method.mode === "simulation" && !!simulationStreams?.length && (
            <details>
              <summary>
                {simulationStreams.length} imported stream records
              </summary>
              <div className="entry-help-caption">
                <span>About validation</span>
                <EntryHelp label="Meaning of simulation validation">
                  Field validation only; this importer does not establish mass or
                  energy balance closure.
                </EntryHelp>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Stream</th>
                      <th>kg/h</th>
                      <th>°C</th>
                      <th>bar abs</th>
                      <th>Phase</th>
                    </tr>
                  </thead>
                  <tbody>
                    {simulationStreams.slice(0, 100).map((stream) => (
                      <tr key={stream.stream_id}>
                        <td>{stream.stream_id}</td>
                        <td>{stream.mass_flow_kg_h}</td>
                        <td>{stream.temperature_c}</td>
                        <td>{stream.pressure_bar_abs}</td>
                        <td>{stream.phase}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {simulationStreams.length > 100 && (
                <p>Showing the first 100 records.</p>
              )}
            </details>
          )}

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
          <div className="entry-help-caption">
            <span>About AI review</span>
            <EntryHelp label="AI review and data sharing">
              AI review sends this description and extracted equipment names, tags
              and endpoints to the configured AI provider. It runs only on click;
              no web research. Numerical balances remain deterministic.
            </EntryHelp>
          </div>
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
      {method.mode !== "simulation" && busy === "parse" && (
        <p role="status">{status}</p>
      )}
      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}
      <div className="equipment-inspection">
          <h3>Equipment list</h3>
          {report && (<>
          {report.entities.some((entity) => entity.kind === "equipment") ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Equipment tag</th>
                    <th>Details</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {report.entities.filter((entity) => entity.kind === "equipment").map((entity) => (
                    <tr key={entity.key}>
                      <td>{entity.identifier}{entity.case ? ` · ${entity.case}` : ""}</td>
                      <td>
                        {entity.values.map((item) => (
                          <div key={item.id}>
                            {item.label}: {String(item.original_value ?? "—")} {item.original_unit}
                          </div>
                        ))}
                      </td>
                      <td>{entity.id_evidence.sheet}!{entity.id_evidence.cell}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p>No equipment identified in this workbook.</p>
          )}
          </>)}
        </div>
    </section>
  );
}
