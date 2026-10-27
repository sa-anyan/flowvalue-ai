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
};
export const workspaceKey = "flowvalue-workspace-v1";
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
      value.project.study &&
      (value.project.study.schema_version !== "flowvalue-study-v1" ||
        !value.project.study.design_basis ||
        !Array.isArray(value.project.study.cost_items) ||
        !Array.isArray(value.project.study.evidence))
    )
      return null;
    if (
      value.native_import &&
      (!Array.isArray(value.native_import.units) ||
        !Array.isArray(value.native_import.streams) ||
        !Array.isArray(value.native_import.warnings))
    )
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
