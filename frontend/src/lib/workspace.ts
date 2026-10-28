import type { BalanceAttachment } from "./balance";
import type { AssessmentRequest, Stream, EquipmentSpec } from "./assessment";
export type NativeImport = {
  streams: Stream[];
  equipment: EquipmentSpec[];
  units: {
    unit_id: string;
    native_id: string;
    native_type: string;
    x: number;
    y: number;
    equipment: EquipmentSpec | null;
    missing_inputs: string[];
    warnings: string[];
  }[];
  warnings: string[];
  source: string;
};
export type Workspace = {
  project: AssessmentRequest;
  streams: Stream[];
  native_import: NativeImport | null;
  balance_import?: BalanceAttachment | null;
};
// New empty-first workspace generation. Older active drafts remain archived under v1.
export const workspaceKey = "flowvalue-workspace-v2";
export const balanceDraftKey = "flowvalue-balance-draft-v2";
export function readBalanceDraft(): BalanceAttachment | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(balanceDraftKey) || "null");
    return isBalanceAttachment(value) ? value : null;
  } catch {
    return null;
  }
}
export function writeBalanceDraft(value: BalanceAttachment | null) {
  try {
    if (value) sessionStorage.setItem(balanceDraftKey, JSON.stringify(value));
    else sessionStorage.removeItem(balanceDraftKey);
  } catch {
    /* in-memory parsing remains available */
  }
}
export function readWorkspace(): Workspace | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(workspaceKey) || "null");
    if (
      !value ||
      !Array.isArray(value.project?.costing?.equipment) ||
      !value.project?.financial ||
      !Array.isArray(value.streams)
    )
      return null;
    if (
      value.project.legacy_reference &&
      (value.project.legacy_reference.schema_version !==
        "flowvalue-legacy-reference-v1" ||
        !Array.isArray(value.project.legacy_reference.sheets) ||
        !value.project.legacy_reference.sheets.length ||
        value.project.legacy_reference.sheets.some(
          (s: { name?: string; cells?: unknown }) =>
            !s.name || !s.cells || typeof s.cells !== "object",
        ))
    )
      return null;
    if (
      value.project.study &&
      (value.project.study.schema_version !== "flowvalue-study-v1" ||
        !value.project.study.design_basis ||
        !Array.isArray(value.project.study.cost_items) ||
        !Array.isArray(value.project.study.evidence) ||
        (value.project.study.engineering_cases !== undefined &&
          !Array.isArray(value.project.study.engineering_cases)))
    )
      return null;
    if (
      value.native_import &&
      (!Array.isArray(value.native_import.units) ||
        !Array.isArray(value.native_import.streams) ||
        !Array.isArray(value.native_import.warnings))
    )
      return null;
    if (value.balance_import && !isBalanceAttachment(value.balance_import))
      return null;
    return value;
  } catch {
    return null;
  }
}
export function writeWorkspace(w: Workspace) {
  try {
    sessionStorage.setItem(workspaceKey, JSON.stringify(w));
  } catch {
    /* browser storage unavailable; in-memory editing still works */
  }
}

export function importScopeNotes(
  native: NativeImport,
  equipment: EquipmentSpec[],
): string[] {
  const excluded = native.units
    .filter((u) => !equipment.some((e) => e.unit_id === u.unit_id))
    .map((u) => u.unit_id);
  const extra = equipment
    .filter((e) => !native.units.some((u) => u.unit_id === e.unit_id))
    .map((e) => e.unit_id);
  return [
    ...(extra.length
      ? [
          `MIXED EQUIPMENT SCOPE: ${extra.join(", ")} priced in the current BOM but absent from this native import. Confirm or replace the retained BOM before relying on these economics.`,
        ]
      : []),
    ...(excluded.length
      ? [
          `INCOMPLETE EQUIPMENT SCOPE: ${excluded.join(", ")} excluded from priced CAPEX. Metrics cover only priced equipment; complete estimates before relying on the business case.`,
        ]
      : []),
    ...native.warnings,
    ...native.units.flatMap((u) => u.warnings.map((w) => `${u.unit_id}: ${w}`)),
  ]
    .slice(0, 100)
    .map((n) => n.slice(0, 1500));
}

export function scenarioScopeNotes(
  project: AssessmentRequest,
  native: NativeImport | null,
): string[] {
  if (!native) return project.engineering_notes || [];
  return [
    ...new Set([
      ...importScopeNotes(native, project.costing.equipment),
      ...(project.engineering_notes || []).filter(
        (n) =>
          !n.startsWith("INCOMPLETE EQUIPMENT SCOPE:") &&
          !n.startsWith("MIXED EQUIPMENT SCOPE:"),
      ),
    ]),
  ]
    .slice(0, 100)
    .map((n) => n.slice(0, 1500));
}

export function isBalanceAttachment(
  value: unknown,
): value is BalanceAttachment {
  if (!value || typeof value !== "object") return false;
  const v = value as Partial<BalanceAttachment>;
  return (
    v.report?.schema_version === "flowvalue-balance-v1" &&
    typeof v.report.filename === "string" &&
    Array.isArray(v.report.entities) &&
    Array.isArray(v.report.tables) &&
    Array.isArray(v.report.issues) &&
    Array.isArray(v.report.checks) &&
    Array.isArray(v.report.sheets) &&
    Array.isArray(v.report.declarations) &&
    Array.isArray(v.report.limitations) &&
    v.report.entities.every(
      (e) =>
        e &&
        typeof e.identifier === "string" &&
        e.id_evidence &&
        typeof e.id_evidence.id === "string" &&
        Array.isArray(e.values) &&
        e.values.every(
          (x) =>
            x &&
            typeof x.id === "string" &&
            typeof x.sheet === "string" &&
            typeof x.cell === "string" &&
            Array.isArray(x.header_cells),
        ),
    ) &&
    typeof v.description?.text === "string" &&
    Array.isArray(v.description.questions) &&
    Array.isArray(v.description.findings)
  );
}
