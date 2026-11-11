export type EquipmentSizingTrace = {
  equipment_key: string | null;
  status: string;
  applicability_notes: string[];
};

export function findEquipmentSizingTrace(
  traces: readonly EquipmentSizingTrace[] | undefined,
  equipmentKey: string | undefined,
): EquipmentSizingTrace | undefined {
  if (!equipmentKey) return undefined;
  return traces?.find(trace => trace.equipment_key === equipmentKey);
}
