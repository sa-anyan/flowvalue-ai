import type { EquipmentSpec } from "./assessment";
export type MaterialChoice =
  "unknown" | "carbon_steel" | "ss304" | "ss316l" | "polymer" | "other";
export type UnitService = {
  duty_description: string;
  fluid_composition: string;
  concentration_basis: string;
  phase: "unknown" | "liquid" | "gas" | "multiphase" | "solid";
  normal_temperature_c: number | null;
  design_temperature_c: number | null;
  design_pressure_barg: number | null;
  food_contact: boolean | null;
  cleaning_regime: string;
  corrosion_conditions: string;
  wetted_material: MaterialChoice;
  shell_material: MaterialChoice;
  lining_or_cladding: string;
  material_rationale: string;
  compatibility_reviewed: boolean;
  mechanical_scope_reviewed: boolean;
};
export type EngineeringCase = {
  unit_id: string;
  unit_kind:
    | "heat_exchanger"
    | "vessel"
    | "reactor"
    | "pump"
    | "compressor"
    | "valve"
    | "other";
  service: UnitService;
  proposed_equipment: Record<string, number | string>;
  evidence_ids: string[];
  hypothesis: string;
  counter_evidence: string;
  baseline_history: {
    digest: string;
    reviewed_at: string;
    reviewer: string;
    actor_id: string | null;
    basis: string;
    equipment: EquipmentSpec;
    status: "user_reviewed_preliminary";
  }[];
};
export type UnitReport = {
  unit_id: string;
  unit_kind: string;
  rule_version: string;
  checked_on: string;
  digest: string;
  case: EngineeringCase;
  questions: string[];
  hypothesis: string | null;
  counter_evidence: string | null;
  material_options: { material: string; role: string; source_ids: string[] }[];
  evidence: { evidence_id: string; title: string; kind: string }[];
  sources: {
    id: string;
    title: string;
    url: string;
    reviewed_on: string;
    scope: string;
  }[];
  sizing: {
    sizing: Record<string, number>;
    purchased_equipment_cost_usd: number;
    bare_module_cost_usd: number;
    warnings: string[];
  } | null;
  blockers: string[];
  warnings: string[];
  can_apply_baseline: boolean;
  baseline_status: "not_reviewed" | "current_user_review" | "stale_review";
  notice: string;
};
export type EngineeringResearch = {
  unit_id: string;
  input_digest: string;
  text: string;
  citations: {
    url: string;
    title: string;
    start_index: number;
    end_index: number;
  }[];
  web_search_used: boolean;
  evidence_status: string;
  complete: boolean;
  model: string;
  prompt_version: string;
  generated_at: string;
  notice: string;
};
export const materials: Record<MaterialChoice, string> = {
  unknown: "Not established",
  carbon_steel: "Carbon steel",
  ss304: "Stainless 304",
  ss316l: "Stainless 316L",
  polymer: "Polymer (specify in rationale)",
  other: "Other (specify in rationale)",
};
export function newEngineeringCase(
  unitId: string,
  kind: EngineeringCase["unit_kind"],
  equipment?: EquipmentSpec,
): EngineeringCase {
  return {
    unit_id: unitId,
    unit_kind: kind,
    service: {
      duty_description: "",
      fluid_composition: "",
      concentration_basis: "",
      phase: "unknown",
      normal_temperature_c: null,
      design_temperature_c: null,
      design_pressure_barg: null,
      food_contact: null,
      cleaning_regime: "",
      corrosion_conditions: "",
      wetted_material: "unknown",
      shell_material: "unknown",
      lining_or_cladding: "",
      material_rationale: "",
      compatibility_reviewed: false,
      mechanical_scope_reviewed: false,
    },
    proposed_equipment: equipment
      ? (Object.fromEntries(
          Object.entries(equipment).filter(
            ([, v]) => typeof v === "number" || typeof v === "string",
          ),
        ) as Record<string, number | string>)
      : {},
    evidence_ids: [],
    hypothesis: "",
    counter_evidence: "",
    baseline_history: [],
  };
}
