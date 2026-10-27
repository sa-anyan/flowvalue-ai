export type DesignBasis = {
  description: string;
  product_specification: string;
  location: string;
  site_type: "unknown" | "greenfield" | "integrated" | "brownfield";
  operating_hours_per_year: number | null;
  requirements: string;
  unresolved_questions: string;
  source_context: string;
};
export type Evidence = {
  evidence_id: string;
  title: string;
  kind:
    "assumption" | "publication" | "quotation" | "design_input" | "measurement";
  source_url: string | null;
  reference: string;
  observed_on: string | null;
  reviewer: string;
  limitation: string;
};
export type CostType =
  "capex" | "fixed_opex" | "feedstock" | "utilities" | "other_variable";
export type CostItem = {
  item_id: string;
  description: string;
  category: string;
  cost_type: CostType;
  status:
    "included" | "excluded" | "not_applicable" | "missing" | "unsupported";
  quantity: number | null;
  unit: string;
  rate_usd: number | null;
  allocation_fraction: number;
  cost_arrangement: "incremental" | "allocated_existing" | "charged_elsewhere";
  basis: string;
  evidence_ids: string[];
};
export type Study = {
  schema_version: "flowvalue-study-v1";
  design_basis: DesignBasis;
  evidence: Evidence[];
  cost_items: CostItem[];
  application: {
    ledger_digest: string;
    reviewer: string;
    applied_on: string;
    totals: Record<string, number>;
  } | null;
};
export type StudyReview = {
  digest: string;
  totals_usd: Record<CostType, number>;
  rows: {
    item_id: string;
    amount_usd: number | null;
    counted: boolean;
    issues: string[];
    status: string;
  }[];
  opex_application_blockers: string[];
  can_apply_opex: boolean;
  questions: string[];
  warnings: string[];
  application_current: boolean;
  notice: string;
};
export function newStudy(): Study {
  return {
    schema_version: "flowvalue-study-v1",
    design_basis: {
      description: "",
      product_specification: "",
      location: "",
      site_type: "unknown",
      operating_hours_per_year: null,
      requirements: "",
      unresolved_questions: "",
      source_context: "",
    },
    evidence: [],
    cost_items: [],
    application: null,
  };
}
export const costTypes: Record<CostType, string> = {
  capex: "CAPEX planning (not applied)",
  fixed_opex: "FCOP · fixed OPEX/year",
  feedstock: "VCOP · feedstock/year",
  utilities: "VCOP · utilities/year",
  other_variable: "VCOP · other/year",
};
export function newCostItem(id: string, type: CostType): CostItem {
  return {
    item_id: id,
    description: "New cost item",
    category: "Other",
    cost_type: type,
    status: "missing",
    quantity: null,
    unit: type === "capex" ? "units" : "units/year",
    rate_usd: null,
    allocation_fraction: 1,
    cost_arrangement: "incremental",
    basis: "",
    evidence_ids: [],
  };
}
