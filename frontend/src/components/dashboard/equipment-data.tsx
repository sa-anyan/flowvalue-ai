import Link from "next/link";
import { equipmentRegister } from "@/lib/balance-register";
import type { BalanceReport, BalanceEvidence } from "@/lib/balance";

const source = (value: BalanceEvidence) => `${value.workbook} · ${value.sheet}!${value.cell}`;

export function EquipmentData({ report }: { report: BalanceReport | null }) {
  const equipment = report ? equipmentRegister(report) : [];
  return (
    <section className="panel" style={{ padding: 28 }}>
      <div className="panel-heading"><h1>Equipment</h1><Link href="/entry">Upload workbook</Link></div>
      {!report ? <p>Upload a workbook on Entry to inspect its equipment.</p> : <>
        <p>{report.filename} · {equipment.length} scoped equipment records</p>
        <div className="table-scroll"><table>
          <thead><tr><th>Equipment tag</th><th>Stream details</th><th>Worksheet / cell</th></tr></thead>
          <tbody>{equipment.flatMap(({ entity, streams }) => {
            const observations = streams.length ? streams.map((stream) => {
              const description = stream.values.find((value) => value.property === "description" || value.property === "name");
              return { stream: stream.identifier, evidence: description ?? stream.id_evidence, text: description?.original_value ?? "No description supplied" };
            }) : entity.values.filter((value) => value.property === "description" || value.property === "name").map((value) => ({ stream: /^Stream\s+(.+?)(?:\s*\||$)/i.exec(value.label)?.[1] ?? "—", evidence: value, text: value.original_value }));
            const rows = observations.length ? observations : [{ stream: "—", evidence: entity.id_evidence, text: "No associated stream description" }];
            return rows.map((observation, index) => (
              <tr key={`${entity.key}:${observation.evidence.id}:${index}`}>
                {index === 0 && <th scope="rowgroup" rowSpan={rows.length}>{entity.identifier}<small className="block">{entity.id_evidence.sheet}</small></th>}
                <td><strong>Stream {observation.stream}</strong><div>{String(observation.text ?? "—")}</div></td>
                <td>{source(observation.evidence)}</td>
              </tr>
            ));
          })}</tbody>
        </table></div>
        {!equipment.length && <p>No equipment identified in this workbook.</p>}
      </>}
    </section>
  );
}
