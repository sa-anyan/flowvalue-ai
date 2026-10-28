"use client";

import type { ReactNode } from "react";

/**
 * One row-spanned tag cell per unique equipment ID. Repeated evidence is
 * displayed underneath the same tag and never counted as extra equipment.
 */
export type EquipmentObservation = {
  id: string;
  description: string;
  source?: string | null;
  requirements?: string | null;
};

export type EquipmentRegisterItem = {
  tag: string;
  equipmentType?: string | null;
  observations: EquipmentObservation[];
};

export function GroupedEquipmentTable({
  equipment,
}: {
  equipment: EquipmentRegisterItem[];
}) {
  const groups = new Map<string, EquipmentRegisterItem>();
  for (const item of equipment) {
    const key = item.tag.trim().toUpperCase();
    if (!key) continue;
    const previous = groups.get(key);
    if (previous) {
      previous.observations.push(...item.observations);
      if (!previous.equipmentType && item.equipmentType)
        previous.equipmentType = item.equipmentType;
    } else {
      groups.set(key, {
        tag: item.tag,
        equipmentType: item.equipmentType,
        observations: [...item.observations],
      });
    }
  }
  return (
    <div className="overflow-x-auto">
      <p className="mb-2 text-sm">
        Unique equipment count: <strong>{groups.size}</strong>
      </p>
      <table className="w-full border-collapse text-left text-sm">
        <thead>
          <tr>
            <th scope="col" className="border p-2">Equipment tag</th>
            <th scope="col" className="border p-2">Type</th>
            <th scope="col" className="border p-2">Occurrence</th>
            <th scope="col" className="border p-2">Description</th>
            <th scope="col" className="border p-2">Requirements</th>
            <th scope="col" className="border p-2">Source</th>
          </tr>
        </thead>
        <tbody>
          {Array.from(groups.values()).map((item) => {
            const observations = item.observations.length
              ? item.observations
              : [{ id: "none", description: "No source observations" }];
            return observations.map((observation, index) => (
              <tr key={item.tag + ":" + observation.id + ":" + index}>
                {index === 0 && (
                  <>
                    <th
                      scope="rowgroup"
                      rowSpan={observations.length}
                      className="border p-2 align-middle font-semibold"
                    >
                      {item.tag}
                    </th>
                    <td
                      rowSpan={observations.length}
                      className="border p-2 align-middle"
                    >
                      {item.equipmentType ?? "Review required"}
                    </td>
                  </>
                )}
                <td className="border p-2">{index + 1}</td>
                <td className="border p-2">{observation.description}</td>
                <td className="border p-2">{observation.requirements ?? "—"}</td>
                <td className="border p-2">{observation.source ?? "—"}</td>
              </tr>
            ));
          })}
        </tbody>
      </table>
    </div>
  );
}
