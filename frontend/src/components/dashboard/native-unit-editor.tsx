"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/client-api";
import {
  apiError,
  defaults,
  fieldLabels,
  kindLabels,
  type Kind,
  type EquipmentSpec,
  type AssessmentRequest,
} from "@/lib/assessment";
import type { NativeImport } from "@/lib/workspace";

const engineeringDefaults = new Set([
  "height_diameter_ratio",
  "allowable_stress_mpa",
  "weld_efficiency",
  "lmtd_correction_factor",
  "efficiency",
  "isentropic_efficiency",
  "heat_capacity_ratio",
  "reference_cepci",
]);
function seed(kind: Kind, existing: EquipmentSpec | undefined, index: number) {
  return Object.fromEntries(
    Object.entries(defaults[kind]).map(([k, v]) => [
      k,
      existing?.[k] !== undefined
        ? String(existing[k])
        : engineeringDefaults.has(k)
          ? String(k === "reference_cepci" ? index : v)
          : "",
    ]),
  );
}
export function NativeUnitEditor({
  unit,
  project,
  onProject,
}: {
  unit: NativeImport["units"][number];
  project: AssessmentRequest;
  onProject: (p: AssessmentRequest) => void;
}) {
  const existing = project.costing.equipment.find(
    (e) => e.unit_id === unit.unit_id,
  );
  const type = unit.native_type.toLowerCase();
  const initial: Kind =
    existing?.kind ||
    (type.includes("reactor")
      ? "reactor"
      : type.includes("vessel") || type.includes("tank")
        ? "vessel"
        : type.includes("heatexchanger")
          ? "heat_exchanger"
          : type.includes("compressor")
            ? "compressor"
            : type.includes("pump")
              ? "pump"
              : "quoted");
  const [kind, setKind] = useState<Kind>(initial);
  const [values, setValues] = useState(() =>
    seed(initial, existing, project.costing.settings.cepci_current),
  );
  const [material, setMaterial] = useState(
    existing?.material || "carbon_steel",
  );
  const [quantity, setQuantity] = useState(existing?.quantity || 1);
  const [basis, setBasis] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function apply() {
    if (!confirmed || !basis.trim()) return;
    setBusy(true);
    setError("");
    try {
      const spec: EquipmentSpec = {
        kind,
        unit_id: unit.unit_id,
        material,
        quantity,
        ...Object.fromEntries(
          Object.entries(values).map(([k, v]) => [k, Number(v)]),
        ),
        ...(kind === "quoted"
          ? { source: `User supplied estimate: ${basis}` }
          : {}),
      };
      const equipment = existing
        ? project.costing.equipment.map((e) =>
            e.unit_id === unit.unit_id ? spec : e,
          )
        : [...project.costing.equipment, spec];
      const r = await apiFetch("/api/costing/bom", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...project.costing, equipment }),
      });
      if (!r.ok) throw Error(await apiError(r));
      onProject({
        ...project,
        costing: { ...project.costing, equipment },
        engineering_notes: [
          ...(project.engineering_notes || []).filter(
            (n) => !n.startsWith(`ENGINEERING REVIEW ${unit.unit_id}:`),
          ),
          `ENGINEERING REVIEW ${unit.unit_id}: ${basis.trim()}. User-confirmed inputs and scope; not code certification.`,
        ].slice(-100),
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to validate equipment");
    } finally {
      setBusy(false);
    }
  }
  return (
    <details>
      <summary>
        {existing
          ? "Edit priced sizing model"
          : "Complete missing sizing model"}{" "}
        · {unit.unit_id}
      </summary>
      {project.engineering_notes?.find((n) =>
        n.startsWith(`ENGINEERING REVIEW ${unit.unit_id}:`),
      ) && (
        <p>
          Active engineering note:{" "}
          {project.engineering_notes.find((n) =>
            n.startsWith(`ENGINEERING REVIEW ${unit.unit_id}:`),
          )}
        </p>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          apply();
        }}
      >
        <p>
          Enter per-unit design inputs. Blank fields are not inferred. Displayed
          efficiency/mechanical factors are editable calculation defaults.
          Review materials, design pressure and excluded internals before
          applying.
        </p>
        <div className="extension-actions">
          <label>
            Equipment model
            <select
              aria-label={`${unit.unit_id} model type`}
              value={kind}
              disabled={busy}
              onChange={(e) => {
                const k = e.target.value as Kind;
                setKind(k);
                setValues(
                  seed(k, undefined, project.costing.settings.cepci_current),
                );
                setConfirmed(false);
              }}
            >
              {Object.entries(kindLabels).map(([k, label]) => (
                <option key={k} value={k}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Quantity
            <input
              aria-label={`${unit.unit_id} reviewed quantity`}
              required
              type="number"
              min={1}
              step={1}
              value={quantity}
              disabled={busy}
              onChange={(e) => {
                setQuantity(Number(e.target.value));
                setConfirmed(false);
              }}
            />
          </label>
          {kind !== "quoted" && (
            <label>
              Material
              <select
                aria-label={`${unit.unit_id} reviewed material`}
                value={material}
                disabled={busy}
                onChange={(e) => {
                  setMaterial(e.target.value);
                  setConfirmed(false);
                }}
              >
                <option value="carbon_steel">Carbon steel</option>
                <option value="stainless_steel">Stainless steel</option>
              </select>
            </label>
          )}
          {Object.entries(values).map(([key, value]) => (
            <label key={key}>
              {fieldLabels[key] || key.replaceAll("_", " ")}
              {engineeringDefaults.has(key) ? " (editable default)" : ""}
              <input
                aria-label={`${unit.unit_id} reviewed ${key}`}
                required
                type="number"
                step="any"
                value={value}
                disabled={busy}
                onChange={(e) => {
                  setValues({ ...values, [key]: e.target.value });
                  setConfirmed(false);
                }}
              />
            </label>
          ))}
        </div>
        <label className="extension-full-label">
          Design / quotation basis
          <textarea
            aria-label={`${unit.unit_id} review basis`}
            required
            maxLength={1000}
            value={basis}
            disabled={busy}
            onChange={(e) => {
              setBasis(e.target.value);
              setConfirmed(false);
            }}
            placeholder="Source, design margin, material choice, date and scope exclusions"
          />
        </label>
        <label className="extension-checkbox">
          <input
            type="checkbox"
            checked={confirmed}
            disabled={busy}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          I reviewed these inputs and the equipment cost scope.
        </label>
        <Button type="submit" disabled={busy || !confirmed || !basis.trim()}>
          {busy ? "Validating…" : `Validate & apply ${unit.unit_id}`}
        </Button>
        {error && (
          <p role="alert" className="engineering-warning">
            {error}
          </p>
        )}
      </form>
    </details>
  );
}
