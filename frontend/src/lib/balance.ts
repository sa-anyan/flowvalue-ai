export type EvidenceStatus = "verified" | "inferred" | "unresolved";
export type BalanceEvidence = {
  id: string;
  workbook: string;
  sheet: string;
  cell: string;
  header_cells: string[];
  original_value: string | number | boolean | null;
  original_unit: string | null;
  normalized_value: string | number | boolean | null;
  normalized_unit: string | null;
  formula: string | null;
  cached: boolean;
  property: string;
  label: string;
  component: string | null;
  status: EvidenceStatus;
  note: string;
};
export type BalanceIssue = {
  code: string;
  status: EvidenceStatus;
  message: string;
  evidence_ids: string[];
};
export type BalanceReport = {
  schema_version: "flowvalue-balance-v1";
  parser_version: string;
  filename: string;
  sha256: string;
  sheets: {
    name: string;
    rows: number;
    columns: number;
    hidden: boolean;
    tables: number;
    nonempty_cells: number;
    extracted_cells: number;
  }[];
  tables: {
    id: string;
    sheet: string;
    range: string;
    orientation: string;
    kind: string;
    status: EvidenceStatus;
  }[];
  entities: {
    key: string;
    kind: "material" | "energy" | "equipment";
    identifier: string;
    case: string;
    table: string;
    id_evidence: BalanceEvidence;
    values: BalanceEvidence[];
    status: EvidenceStatus;
    stream_keys?: string[];
  }[];
  connections?: { key: string; stream_key: string; equipment_key: string | null; role: "source" | "destination" | "mention"; basis: string; evidence_ids: string[]; status: EvidenceStatus; note: string }[];
  declarations: BalanceEvidence[];
  issues: BalanceIssue[];
  checks: {
    name: string;
    scope: string;
    status: EvidenceStatus;
    message: string;
    residual: number | null;
    unit: string | null;
    evidence_ids: string[];
  }[];
  coverage: string;
  limitations: string[];
};
export type BalanceDescription = {
  text: string;
  reviewed_text: string;
  findings: BalanceIssue[];
  questions: string[];
  model: string | null;
  reviewed_at: string | null;
};
export type BalanceAttachment = {
  report: BalanceReport;
  description: BalanceDescription;
};
export const emptyDescription: BalanceDescription = {
  text: "",
  reviewed_text: "",
  findings: [],
  questions: [],
  model: null,
  reviewed_at: null,
};
export function descriptionIsCurrent(value: BalanceAttachment) {
  return (
    value.description.text === value.description.reviewed_text &&
    !!value.description.reviewed_at
  );
}
