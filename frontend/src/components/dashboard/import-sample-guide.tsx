"use client";

import { useState } from "react";
import { Download, Eye, FileCheck2, LockKeyhole, RotateCcw } from "lucide-react";
import type { ImportMethodId } from "@/lib/import-methods";
import { getImportSample } from "@/lib/import-samples";
import { EntryHelp } from "./entry-help";

export function ImportSampleGuide({
  methodId,
  locked,
  onLock,
  onUnlock,
}: {
  methodId: ImportMethodId;
  locked: boolean;
  onLock: () => void;
  onUnlock: () => void;
}) {
  const sample = getImportSample(methodId);
  const [previewOpen, setPreviewOpen] = useState(false);
  return (
    <div className="import-setup" aria-label="Import source confirmation">
      {sample ? (
        <>
          <div className="import-setup-heading">
            <div>
              <div className="entry-inline-help">
                <strong>Sample format</strong>
                <EntryHelp label={`About the ${sample.name} example`}>
                  {sample.notes}
                </EntryHelp>
              </div>
              <span>{sample.name}</span>
            </div>
            <span className="import-sample-kind">
              {sample.kind === "tested-fixture" ? "Test fixture" : sample.kind === "generic-example" ? "Generic reference" : "Example"}
            </span>
          </div>
          <div className="import-setup-actions">
            <a href={sample.downloadUrl} download className="import-setup-link">
              <Download size={15} /> Download sample
            </a>
            <button type="button" className="import-setup-link" aria-expanded={previewOpen}
              onClick={() => setPreviewOpen((value) => !value)}>
              <Eye size={15} /> {previewOpen ? "Hide preview" : "Preview sample"}
            </button>
          </div>
          {previewOpen && (
            <div className="import-sample-preview" aria-label={sample.previewTitle}>
              <strong>{sample.previewTitle}</strong>
              <div className="table-scroll">
                <table>
                  <thead><tr>{sample.columns.map((col) => <th key={col}>{col}</th>)}</tr></thead>
                  <tbody>{sample.previewRows.map((row, i) =>
                    <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>)}</tbody>
                </table>
              </div>
              <div className="entry-help-caption">
                <span>Preview guidance</span>
                <EntryHelp label="How the preview differs from the downloaded file">
                  Structure preview only; download the file for all rows and worksheets.
                </EntryHelp>
              </div>
            </div>
          )}

        </>
      ) : (
        <div className="import-sample-missing">
          <strong>No parser-specific sample is available yet</strong>
          <EntryHelp label="Why there is no sample">
            This source is not supported for file extraction. We have not created a validated template for it, so there is no sample to download.
          </EntryHelp>
        </div>
      )}
      <div className="entry-help-caption">
        <span>About samples</span>
        <EntryHelp label="How FlowValue uses sample files">
          Samples illustrate expected structure; FlowValue uses rule-based parsing and validation, not a model trained on these files.
        </EntryHelp>
      </div>
      <div className="import-lock-row">
        {locked ? (
          <div className="import-locked" role="status">
            <FileCheck2 size={16} /> Source locked in
            <button type="button" onClick={onUnlock}><RotateCcw size={13} /> Change</button>
          </div>
        ) : (
          <button type="button" className="import-lock-button" onClick={onLock}>
            <LockKeyhole size={15} /> Lock in selected source
          </button>
        )}
        {!locked && (
          <EntryHelp label="Is a sample download required?">
            Preview or download the sample first, or continue without it.
          </EntryHelp>
        )}
      </div>
    </div>
  );
}
