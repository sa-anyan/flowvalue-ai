"use client";

type Evidence = {
  id: string;
  sheet: string;
  cell: string;
  property: string;
  label: string;
  component?: string | null;
  original_value?: string | number | boolean | null;
  original_unit?: string | null;
  normalized_value?: string | number | boolean | null;
  normalized_unit?: string | null;
  status: "verified" | "inferred" | "unresolved";
};
type EquipmentEntity = {
  kind: "material" | "energy" | "equipment";
  identifier: string;
  values: Evidence[];
};
type Report = { entities: EquipmentEntity[] };
type PropertyRow = {
  tag: string;
  stream: string;
  property: string;
  component: string;
  value: string;
  unit: string;
  source: string;
  status: string;
};
const stringify = (value: Evidence["original_value"]): string =>
  value === null || value === undefined ? "—" : String(value);

/** Group property evidence by tag and then stream, without inventing measurements. */
export function EquipmentPropertiesTable({ report }: { report: Report | null }) {
  if (!report) return <p>No equipment properties uploaded yet.</p>;
  const groups = new Map<string, PropertyRow[]>();
  for (const entity of report.entities) {
    if (entity.kind === "energy") continue;
    if (entity.kind === "material") {
      const description = entity.values.find((value) => value.property === "description");
      const mentioned = description && report.entities.some((equipment) => equipment.kind === "equipment" && equipment.values.some((value) => value.property === "description" && value.sheet === description.sheet && value.cell === description.cell));
      if (mentioned) continue;
    }
    const tag = entity.kind === "material" ? `Unassigned · Stream ${entity.identifier} · ${entity.values[0]?.sheet ?? "Unknown worksheet"}` : entity.identifier.trim().toUpperCase();
    if (!tag) continue;
    if (!groups.has(tag)) groups.set(tag, []);
    const rows = groups.get(tag)!;
    for (const value of entity.values ?? []) {
      if (value.property === "identifier" || value.property === "description" || value.property === "type") continue;
      const stream = /^Stream\s+([^|: ]+)/i.exec(value.label)?.[1];
      if (!stream) continue;
      rows.push({
        tag,
        stream,
        property: value.property.replaceAll("_", " "),
        component: value.component?.trim() || (value.property.startsWith("component_") ? value.label.split("|").slice(1).join("|").trim() || "Unresolved" : "—"),
        value: stringify(value.original_value),
        unit: value.original_unit ?? "—",
        source: value.sheet + "!" + value.cell,
        status: value.status,
      });
    }
  }
  const ordered = [...groups].sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true }));
  return (
    <section aria-label="Equipment properties" className="space-y-3">
      <h2 className="text-lg font-semibold">Equipment properties</h2>
      <p className="text-sm opacity-75">
        {ordered.filter(([tag]) => !tag.startsWith("Unassigned ·")).length} unique equipment items. Untagged streams are listed as unassigned. Measurements are stream observations,
        not automatically selected equipment design conditions.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr>
              {["Equipment tag", "Stream number", "Component", "Property", "Value", "Unit", "Source cell", "Status"].map((heading) =>
                <th key={heading} scope="col" className="border p-2">{heading}</th>
              )}
            </tr>
          </thead>
          <tbody>
            {ordered.map(([tag, observations]) => {
              const data = observations.length ? observations : [{
                tag, stream: "—", component: "—", property: "No parsed numerical properties",
                value: "—", unit: "—", source: "—", status: "unresolved",
              }];
              const sorted = [...data].sort((a,b) => a.stream.localeCompare(b.stream, undefined, { numeric: true }));
              return sorted.map((entry, index) => (
                <tr key={tag + ":" + entry.stream + ":" + entry.property + ":" + entry.source + ":" + index}>
                  {index === 0 && (
                    <th scope="rowgroup" rowSpan={sorted.length} className="border p-2 align-middle font-semibold">
                      {tag}
                    </th>
                  )}
                  <td className="border p-2">{entry.stream}</td>
                  <td className="border p-2">{entry.component}</td>
                  <td className="border p-2">{entry.property}</td>
                  <td className="border p-2 tabular-nums">{entry.value}</td>
                  <td className="border p-2">{entry.unit}</td>
                  <td className="border p-2">{entry.source}</td>
                  <td className="border p-2">{entry.status}</td>
                </tr>
              ));
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
