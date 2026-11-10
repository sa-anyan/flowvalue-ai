export type Row = Record<string, unknown>;
export const object = (v: unknown): Row =>
  v && typeof v === "object" && !Array.isArray(v) ? (v as Row) : {};
export const array = (v: unknown): Row[] =>
  Array.isArray(v) ? v.map(object) : [];
export const number = (v: unknown) =>
  v === null ||
  v === undefined ||
  v === "" ||
  typeof v === "boolean" ||
  !Number.isFinite(Number(v))
    ? null
    : Number(v);
export const amount = (v: unknown) =>
  number(v) === null
    ? "—"
    : new Intl.NumberFormat("en-GB", {
        notation: "compact",
        maximumFractionDigits: 2,
      }).format(Number(v));
export const full = (v: unknown) =>
  number(v) === null
    ? "—"
    : new Intl.NumberFormat("en-GB", { maximumFractionDigits: 3 }).format(
        Number(v),
      );
export const meceMethods: Record<string, string> = {
  product_sales: "Sell a product",
  processing_services: "Get paid to process material",
  capacity_availability: "Get paid to reserve capacity",
  infrastructure_usage: "Charge for using a facility",
  environmental_attributes: "Sell environmental credits",
  other_contractual_income: "Receive another payment",
};
export const meceFormula: Record<string, string> = {
  product_sales:
    "Stream rate × operating hours × saleable share × sold share × price",
  processing_services: "Billable processing rate × operating hours × tariff",
  capacity_availability:
    "Reserved capacity × rate × billing periods × qualifying availability",
  infrastructure_usage: "Billable usage × tariff × billing periods",
  environmental_attributes: "Eligible credits sold × price per credit",
  other_contractual_income:
    "Contractual fixed payment + billable quantity × contractual rate",
};
export type IncomeLine = {
  category?: string;
  role?: "main_product" | "byproduct";
  method_form?: Row | null;
  price_review?: Row | null;
  original?: Row;
  id: string;
  name: string;
  kind: "product" | "service";
  stream_key: string | null;
  component: string | null;
  rate: number | null;
  rate_unit: string;
  price: number | null;
  price_unit: string;
  price_period?: string;
  sold_fraction: number;
  saleable_fraction: number;
  allocation_fraction: number;
  rationale: string;
  advanced?: boolean;
  confirmRate?: boolean;
};
export function revenueLines(config: Row): IncomeLine[] {
  return [
    ...array(config.sales).map((r) => ({ r, kind: "product" as const })),
    ...array(config.commercial_lines).map((r) => ({
      r,
      kind: "service" as const,
    })),
  ].map(({ r, kind }) => {
    const terms = array(r.years),
      manual = object(r.manual_rate);
    return {
      category:
        kind === "product"
          ? "product_sales"
          : String(r.category || "processing_services"),
      role: r.role === "byproduct" ? "byproduct" : "main_product",
      method_form: r.method_form ? object(r.method_form) : null,
      price_review: r.price_review ? object(r.price_review) : null,
      original: r,
      id: String(r.id),
      name: String(r.name || r.id),
      kind,
      stream_key: r.stream_key ? String(r.stream_key) : null,
      component: r.component ? String(r.component) : null,
      rate: number(manual.value),
      rate_unit: String(manual.unit || "m3/h"),
      price: number(
        kind === "product"
          ? r.unit_price
          : object(r.method_form).subtype === "fixed"
            ? terms[0]?.fixed_payment
            : terms[0]?.rate,
      ),
      price_unit: String(r.quantity_unit || "m3"),
      price_period: String(
        object(r.price_basis).price_period ||
          object(config.price_basis).price_period ||
          "",
      ),
      sold_fraction: number(r.sold_fraction) ?? 1,
      saleable_fraction: number(r.saleable_fraction) ?? 1,
      allocation_fraction: number(r.allocation_fraction) ?? 1,
      rationale: String(r.rationale || "Explicit user revenue rate assumption"),
      confirmRate: Boolean(r.manual_rate) && manual.confirmed_by_user !== true,
      advanced:
        kind === "product"
          ? r.price_mode !== "assumed_price"
          : !r.method_form &&
            terms.some(
              (t) =>
                Number(t.minimum_payment || 0) !== 0 ||
                Number(t.minimum_quantity || 0) !== 0 ||
                [
                  "rate",
                  "fixed_payment",
                  "availability",
                  "quantity",
                  "escalation",
                ].some((k) => t[k] !== terms[0]?.[k]),
            ),
    };
  });
}

export function requiresTerms(line: IncomeLine) {
  const first = array(line.original?.years)[0] || {};
  return (
    Boolean(line.method_form) ||
    !["product_sales", "processing_services"].includes(
      line.category || "product_sales",
    ) ||
    (line.kind === "service" &&
      (Number(first.fixed_payment || 0) !== 0 ||
        Boolean(
          line.original?.rate_period &&
            line.original.rate_period !== "per_unit",
        )))
  );
}
