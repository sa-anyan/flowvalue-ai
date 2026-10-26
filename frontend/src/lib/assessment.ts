import type { AdvisorContext } from "@/components/dashboard/universal-advisor";
export type Kind =
  "quoted" | "heat_exchanger" | "vessel" | "reactor" | "pump" | "compressor";
export type EquipmentSpec = {
  unit_id: string;
  kind: Kind;
  material?: string;
  quantity?: number;
  [key: string]: number | string | boolean | undefined;
};
export type Incentive = {
  enabled: boolean;
  name: string;
  rate_usd_per_unit: number;
  eligible_fraction: number;
  start_year: number;
  duration_years: number;
  treatment: "cash_payment" | "tax_offset";
  eligibility_confirmed: boolean;
  basis: string;
};
export const defaultIncentive: Incentive = {
  enabled: false,
  name: "User-defined production credit",
  rate_usd_per_unit: 0,
  eligible_fraction: 1,
  start_year: 1,
  duration_years: 10,
  treatment: "cash_payment",
  eligibility_confirmed: false,
  basis: "",
};
export type Financial = {
  incentive?: Incentive;
  fixed_opex_usd_per_year: number;
  variable_opex_usd_per_year: number;
  feedstock_opex_usd_per_year: number;
  utility_opex_usd_per_year: number;
  plant_capacity_units_per_year: number;
  capacity_factor: number;
  product_selling_price_usd_per_unit: number;
  tax_rate: number;
  discount_rate: number;
  operating_years: number;
  depreciation_years?: number | null;
};
export type AssessmentRequest = {
  engineering_notes?: string[];
  is_demo: boolean;
  advisor_context?: AdvisorContext;
  costing: {
    equipment: EquipmentSpec[];
    settings: {
      capital_cost_multiplier?: number;
      cepci_current: number;
      cepci_base: number;
      allow_extrapolation: boolean;
    };
  };
  financial: Financial;
  simulation: { iterations: number; variation_fraction: number; seed: number };
};
export type BOMItem = {
  unit_id: string;
  kind: Kind;
  material: string;
  quantity: number;
  sizing: Record<string, number>;
  correlation_size: number;
  correlation_size_unit: string;
  material_factor: number;
  pressure_factor: number;
  purchased_equipment_cost_usd: number;
  bare_module_cost_usd: number;
  warnings: string[];
};
export type CashFlow = {
  year: number;
  revenue_usd: number;
  opex_usd: number;
  taxes_usd: number;
  free_cash_flow_usd: number;
  cumulative_free_cash_flow_usd: number;
  cumulative_discounted_free_cash_flow_usd: number;
};
export type Assessment = {
  bom: {
    items: BOMItem[];
    total_bare_module_cost_usd: number;
    total_purchased_equipment_cost_usd: number;
  };
  financial: {
    npv_usd: number;
    irr: number | null;
    payback_years: number | null;
    discounted_payback_years: number | null;
    lcop_usd_per_unit: number;
    cash_flows: CashFlow[];
    assumptions: string[];
    warnings: string[];
  };
  uncertainty: {
    iterations: number;
    seed: number;
    p10_npv_usd: number;
    p50_npv_usd: number;
    p90_npv_usd: number;
    probability_positive_npv: number;
    histogram: {
      lower_npv_usd: number;
      upper_npv_usd: number;
      count: number;
    }[];
    warnings: string[];
  } | null;
};
export type Stream = {
  stream_id: string;
  mass_flow_kg_h: number;
  temperature_c: number;
  pressure_bar_abs: number;
  phase: string;
  source_unit?: string | null;
  destination_unit?: string | null;
};
export const kindLabels: Record<Kind, string> = {
  quoted: "External library / quote",
  heat_exchanger: "Heat exchanger",
  vessel: "Pressure vessel",
  reactor: "Reactor shell",
  pump: "Centrifugal pump",
  compressor: "Compressor",
};
export const defaults: Record<Kind, Record<string, number>> = {
  quoted: {
    purchased_cost_usd: 100000,
    installed_cost_usd: 300000,
    reference_cepci: 800,
  },
  heat_exchanger: {
    duty_kw: 1000,
    overall_u_w_m2_k: 500,
    lmtd_k: 20,
    lmtd_correction_factor: 1,
    design_pressure_barg: 0,
  },
  vessel: {
    volume_m3: 30,
    height_diameter_ratio: 3,
    design_pressure_barg: 10,
    allowable_stress_mpa: 94.4,
    weld_efficiency: 0.9,
  },
  reactor: {
    volume_m3: 30,
    height_diameter_ratio: 3,
    design_pressure_barg: 10,
    allowable_stress_mpa: 94.4,
    weld_efficiency: 0.9,
  },
  pump: {
    volumetric_flow_m3_h: 360,
    density_kg_m3: 1000,
    head_m: 100,
    efficiency: 0.8,
    design_pressure_barg: 0,
  },
  compressor: {
    mass_flow_kg_s: 10,
    inlet_temperature_k: 300,
    inlet_pressure_bar_abs: 1,
    outlet_pressure_bar_abs: 4,
    molecular_weight_kg_kmol: 28,
    heat_capacity_ratio: 1.4,
    isentropic_efficiency: 0.75,
  },
};
export const fieldLabels: Record<string, string> = {
  purchased_cost_usd: "External purchased cost · USD/unit",
  installed_cost_usd: "External installed cost · USD/unit",
  reference_cepci: "External reference CEPCI",
  duty_kw: "Duty · kW",
  overall_u_w_m2_k: "Overall U · W/m²/K",
  lmtd_k: "LMTD · K",
  lmtd_correction_factor: "LMTD correction factor",
  design_pressure_barg: "Design pressure · barg",
  volume_m3: "Volume · m³",
  height_diameter_ratio: "Height / diameter",
  allowable_stress_mpa: "Allowable stress · MPa",
  weld_efficiency: "Weld efficiency",
  volumetric_flow_m3_h: "Volume flow · m³/h",
  density_kg_m3: "Density · kg/m³",
  head_m: "Head · m",
  efficiency: "Pump efficiency",
  mass_flow_kg_s: "Mass flow · kg/s",
  inlet_temperature_k: "Inlet temperature · K",
  inlet_pressure_bar_abs: "Inlet pressure · bar abs",
  outlet_pressure_bar_abs: "Outlet pressure · bar abs",
  molecular_weight_kg_kmol: "Molecular weight · kg/kmol",
  heat_capacity_ratio: "Heat capacity ratio",
  isentropic_efficiency: "Isentropic efficiency",
};
export const usd = (value: number, compact = false) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: compact ? "compact" : "standard",
    maximumFractionDigits: compact ? 2 : 0,
  }).format(value);
export const percent = (value: number) => `${(value * 100).toFixed(1)}%`;
export async function apiError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    return Array.isArray(data.detail)
      ? data.detail
          .slice(0, 5)
          .map(
            (e: { loc: (string | number)[]; msg: string }) =>
              `${e.loc.filter((x) => x !== "body").join(" → ")}: ${e.msg}`,
          )
          .join("; ")
      : (data.detail ?? `Request failed (${response.status})`);
  } catch {
    return `Request failed (${response.status}). Please check the backend.`;
  }
}
