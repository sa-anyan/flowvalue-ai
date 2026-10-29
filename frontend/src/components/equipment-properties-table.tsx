"use client";

import type { BalanceReport } from "@/lib/balance";
import { equipmentPropertyGroups } from "@/lib/balance-register";

export function EquipmentPropertiesTable({ report }: { report: BalanceReport | null }) {
  if (!report) return <p>No equipment properties uploaded yet.</p>;
  const groups = equipmentPropertyGroups(report);
  const equipmentCount = report.entities.filter((entity) => entity.kind === "equipment").length;
  return (
    <section aria-label="Equipment properties" className="space-y-3">
      <h2 className="text-lg font-semibold">Equipment properties</h2>
      <p className="text-sm opacity-75">{equipmentCount} scoped equipment records. Untagged streams remain unassigned. Measurements are stream observations, not equipment design conditions.</p>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm">
          <thead><tr>{["Equipment tag", "Stream number", "Component", "Property", "Value", "Unit", "Source cell", "Status"].map((heading) => <th key={heading} scope="col" className="border p-2">{heading}</th>)}</tr></thead>
          <tbody>{groups.map((group) => (group.rows.length ? group.rows : [{ stream: "—", evidence: null }]).map(({ stream, evidence }, index, rows) => (
            <tr key={`${group.key}:${evidence?.id ?? "empty"}:${index}`}>
              {index === 0 && <th scope="rowgroup" rowSpan={rows.length} className="border p-2 align-middle font-semibold">{group.tag}<small className="block font-normal">{group.sheet}</small></th>}
              <td className="border p-2">{stream}</td>
              <td className="border p-2">{evidence?.component ?? "—"}</td>
              <td className="border p-2">{evidence?.property.replaceAll("_", " ") ?? "No parsed properties"}</td>
              <td className="border p-2 tabular-nums">{String(evidence?.original_value ?? "—")}</td>
              <td className="border p-2">{evidence?.original_unit ?? "—"}</td>
              <td className="border p-2">{evidence ? `${evidence.sheet}!${evidence.cell}` : "—"}</td>
              <td className="border p-2">{evidence?.status ?? "unresolved"}</td>
            </tr>
          )))}</tbody>
        </table>
      </div>
    </section>
  );
}
