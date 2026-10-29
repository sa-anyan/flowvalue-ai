import type { BalanceReport, BalanceEvidence } from "./balance";

export type RegisterEntity = BalanceReport["entities"][number];
export type PropertyGroup = { key: string; tag: string; sheet: string; rows: { stream: string; evidence: BalanceEvidence }[] };
const metadata = new Set(["identifier", "description", "name", "type", "source", "destination", "inlets", "outlets"]);

/** Resolve v3 scoped references once; continue reading pre-v3 saved reports. */
export function equipmentRegister(report: BalanceReport) {
  const byKey = new Map(report.entities.map((entity) => [entity.key, entity]));
  return report.entities.filter((entity) => entity.kind === "equipment").map((entity) => ({
    entity,
    streams: (entity.stream_keys ?? []).map((key) => byKey.get(key)).filter((item): item is RegisterEntity => !!item && item.kind === "material"),
  }));
}

export function equipmentPropertyGroups(report: BalanceReport): PropertyGroup[] {
  const groups: PropertyGroup[] = [];
  const assigned = new Set<string>();
  const legacyDescriptions = new Set<string>();
  for (const { entity, streams } of equipmentRegister(report)) {
    const group: PropertyGroup = { key: entity.key, tag: entity.identifier, sheet: entity.id_evidence.sheet, rows: [] };
    if (entity.stream_keys?.length) {
      for (const stream of streams) {
        assigned.add(stream.key);
        for (const evidence of stream.values) if (!metadata.has(evidence.property)) group.rows.push({ stream: stream.identifier, evidence });
      }
    } else {
      for (const evidence of entity.values) {
        if (evidence.property === "description") legacyDescriptions.add(`${evidence.sheet}!${evidence.cell}`);
        const stream = /^Stream\s+([^|: ]+)/i.exec(evidence.label)?.[1];
        if (stream && !metadata.has(evidence.property)) group.rows.push({ stream, evidence });
      }
    }
    groups.push(group);
  }
  for (const stream of report.entities) {
    if (stream.kind !== "material" || assigned.has(stream.key)) continue;
    if (stream.values.some((value) => value.property === "description" && legacyDescriptions.has(`${value.sheet}!${value.cell}`))) continue;
    groups.push({ key: stream.key, tag: `Unassigned · Stream ${stream.identifier}`, sheet: stream.id_evidence.sheet,
      rows: stream.values.filter((value) => !metadata.has(value.property)).map((evidence) => ({ stream: stream.identifier, evidence })) });
  }
  return groups;
}
