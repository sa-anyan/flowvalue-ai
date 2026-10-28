import Link from "next/link";
import type { BalanceReport, BalanceEvidence } from "@/lib/balance";

const source = (value: BalanceEvidence) => `${value.workbook} · ${value.sheet}!${value.cell}`;
const display = (value: BalanceEvidence) => `${value.label}: ${value.original_value ?? "Not extracted"}${value.original_unit ? ` ${value.original_unit}` : ""}`;

export function EquipmentData({ report }: { report: BalanceReport | null }) {
  const equipment = report?.entities.filter((entity) => entity.kind === "equipment") ?? [];
  return (
    <section className="panel" style={{ padding: 28 }}>
      <div className="panel-heading"><h1>Equipment</h1><Link href="/entry">Upload workbook</Link></div>
      {!report ? <p>Upload a workbook on Entry to inspect its equipment.</p> : <>
        <p>{report.filename} · {new Set(equipment.map((item) => item.identifier)).size} equipment tags</p>
        <div className="table-scroll"><table>
          <thead><tr><th>Equipment tag</th><th>Stream details</th><th>Flow rate, pressure, temperature &amp; properties</th><th>Worksheet / cell</th></tr></thead>
          <tbody>{equipment.flatMap((entity) => {
            const descriptions = entity.values.filter((value) => value.property === "description" || value.property === "name");
            return (descriptions.length ? descriptions : [entity.id_evidence]).map((observation, index) => {
              // Link only explicit stream identifiers already extracted from this workbook.
              const streamId = /^Stream\s+(\d+)$/i.exec(observation.label)?.[1];
              const matching = streamId ? report.entities.filter((item) => item.kind === "material" && item.identifier === streamId && item.case === entity.case) : [];
              const properties = matching.flatMap((item) => item.values.filter((value) => typeof value.original_value === "number"));
              return <tr key={`${entity.key}:${observation.id}:${index}`}>
                {index === 0 && <th scope="rowgroup" rowSpan={descriptions.length || 1}>{entity.identifier}</th>}
                <td><strong>{streamId ? `Stream ${streamId}` : observation.label}</strong><div>{String(observation.original_value ?? "No stream description extracted")}</div></td>
                <td>{properties.length ? properties.map((value) => <div key={value.id}>{display(value)}</div>) : "Not extracted"}</td>
                <td><div>{source(observation)}</div>{properties.map((value) => <div key={value.id}>{value.label}: {source(value)}</div>)}</td>
              </tr>;
            });
          })}</tbody>
        </table></div>
        {!equipment.length && <p>No equipment identified in this workbook.</p>}
      </>}
    </section>
  );
}
