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
    return JSON.parse(sessionStorage.getItem(workspaceKey) || "null");
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
  return [
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
