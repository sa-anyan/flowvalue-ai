import type { AssessmentRequest } from "./assessment";
import type { CostItem } from "./study";

export type CapitalGroup =
  | "direct-costs"
  | "indirect-costs"
  | "working-capital"
  | "unclassified";
export const capitalScopes = [
  {
    code: "D01",
    group: "direct-costs",
    label: "Installation",
    prompt:
      "Define installation beyond the equipment module or vendor package. Identify rigging, foundations and labour already included.",
    overlap: true,
  },
  {
    code: "D02",
    group: "direct-costs",
    label: "Instrumentation and control",
    prompt:
      "List field instruments, control system, panels and commissioning. Check vendor skid boundaries.",
    overlap: true,
  },
  {
    code: "D03",
    group: "direct-costs",
    label: "Piping",
    prompt:
      "Establish piping classes, materials, lengths and fittings, or state a preliminary allowance basis.",
    overlap: true,
  },
  {
    code: "D04",
    group: "direct-costs",
    label: "Electrical",
    prompt:
      "Define electrical load, distribution, motor control, cabling and connection scope.",
    overlap: true,
  },
  {
    code: "D05",
    group: "direct-costs",
    label: "Yard improvements",
    prompt:
      "Review earthworks, access, drainage and site preparation for the chosen location.",
    overlap: false,
  },
  {
    code: "D06",
    group: "direct-costs",
    label: "Buildings",
    prompt:
      "Define production, storage, laboratory and office space. Record retained infrastructure at integrated sites.",
    overlap: false,
  },
  {
    code: "D07",
    group: "direct-costs",
    label: "Service facilities",
    prompt:
      "Identify cooling, water treatment, compressed air and other offsite utilities beyond the equipment packages.",
    overlap: true,
  },
  {
    code: "D08",
    group: "direct-costs",
    label: "Land",
    prompt:
      "Record purchase, lease or existing-site treatment, area, region and cost basis.",
    overlap: false,
  },
  {
    code: "I01",
    group: "indirect-costs",
    label: "Engineering and supervision",
    prompt:
      "Define design deliverables, engineering hours, supervision and project management scope.",
    overlap: false,
  },
  {
    code: "I02",
    group: "indirect-costs",
    label: "Construction expenses",
    prompt:
      "Include temporary facilities, accommodation, construction management and site consumables where applicable.",
    overlap: false,
  },
  {
    code: "I03",
    group: "indirect-costs",
    label: "Legal fees and taxes",
    prompt:
      "Identify permits, legal services, duties and non-recoverable taxes for the project jurisdiction.",
    overlap: false,
  },
  {
    code: "I04",
    group: "indirect-costs",
    label: "Contractor fee",
    prompt:
      "State the contracted scope and fee basis. Separate fees already included in quoted packages.",
    overlap: false,
  },
  {
    code: "I05",
    group: "indirect-costs",
    label: "Contingency",
    prompt:
      "Document estimate maturity, uncertainty coverage and the subtotal to which the allowance applies.",
    overlap: false,
  },
  {
    code: "W01",
    group: "working-capital",
    label: "Working capital allowance",
    prompt:
      "Document inventories, receivables, payables, start-up cash and timing. Do not assume a universal percentage of fixed capital.",
    overlap: false,
  },
] as const;
export type CapitalScope = (typeof capitalScopes)[number];
export const capitalGroupLabels: Record<CapitalGroup, string> = {
  "direct-costs": "Direct Costs",
  "indirect-costs": "Indirect Costs",
  "working-capital": "Working Capital",
  unclassified: "Unclassified",
};
const normalize = (s: string) =>
  s
    .trim()
    .toLowerCase()
    .replace(/[’']/g, "")
    .replace(/[\s_-]+/g, " ");
export function capitalGroup(item: CostItem): CapitalGroup {
  const name = normalize(item.category.split(" / ")[0]);
  if (["direct costs", "direct cost"].includes(name)) return "direct-costs";
  if (["indirect costs", "indirect cost"].includes(name))
    return "indirect-costs";
  if (["working capital", "working capital costs"].includes(name))
    return "working-capital";
  return "unclassified";
}
export function capitalScope(item: CostItem): CapitalScope | undefined {
  const named = item.category.split(" / ")[1] || item.description;
  return capitalScopes.find(
    (s) =>
      s.group === capitalGroup(item) && normalize(s.label) === normalize(named),
  );
}
export function capitalAmount(item: CostItem): number | null {
  if (
    item.cost_type !== "capex" ||
    item.status !== "included" ||
    item.cost_arrangement === "charged_elsewhere" ||
    item.quantity === null ||
    item.rate_usd === null ||
    !Number.isFinite(item.quantity) ||
    !Number.isFinite(item.rate_usd) ||
    !Number.isFinite(item.allocation_fraction) ||
    item.quantity > 1e12 ||
    item.rate_usd > 1e12 ||
    item.quantity < 0 ||
    item.rate_usd < 0 ||
    item.allocation_fraction < 0 ||
    item.allocation_fraction > 1
  )
    return null;
  const amount = item.quantity * item.rate_usd * item.allocation_fraction;
  return Number.isFinite(amount) ? amount : null;
}
export function capitalRowIssues(
  item: CostItem,
  project: AssessmentRequest,
): string[] {
  if (["excluded", "not_applicable"].includes(item.status))
    return item.basis.trim()
      ? []
      : ["Record the reason for this scope decision."];
  if (item.cost_arrangement === "charged_elsewhere")
    return item.basis.trim()
      ? []
      : ["Identify the cost owner and where this cost is charged."];
  const issues: string[] = [];
  if (item.status === "missing")
    issues.push("Establish the quantity, rate and costing method.");
  if (item.status === "unsupported")
    issues.push("Obtain a supported method or supplier quotation.");
  if (item.status === "included" && capitalAmount(item) === null)
    issues.push("Complete valid quantity, USD rate and allocation inputs.");
  if (!item.basis.trim())
    issues.push("Record the costing basis and scope boundary.");
  const sources =
    project.study?.evidence.filter((e) =>
      item.evidence_ids.includes(e.evidence_id),
    ) ?? [];
  if (
    !sources.some(
      (e) => e.kind !== "assumption" && (e.reference.trim() || e.source_url),
    )
  )
    issues.push("Link a quotation, design input or other applicable source.");
  if (capitalScope(item)?.overlap && project.costing.equipment.length)
    issues.push(
      "Check overlap with installation, piping or services included in bare-module/vendor costs.",
    );
  if (
    /£|GBP|EUR|€/i.test(item.basis) &&
    !/USD|conversion|exchange|FX/i.test(item.basis)
  )
    issues.push("Document the currency conversion before entering a USD rate.");
  return issues;
}
export function capitalCoverage(project: AssessmentRequest) {
  const items = (project.study?.cost_items ?? []).filter(
    (i) => i.cost_type === "capex",
  );
  return capitalScopes.map((scope) => {
    const rows = items.filter((i) => capitalScope(i)?.code === scope.code);
    const issues = rows.flatMap((i) => capitalRowIssues(i, project));
    const values = rows
      .map(capitalAmount)
      .filter((n): n is number => n !== null);
    return {
      scope,
      rows,
      issues,
      amount: values.length ? values.reduce((a, b) => a + b, 0) : null,
      status: !rows.length
        ? "Not assessed"
        : rows.every((r) => r.status === "not_applicable")
          ? "Not applicable"
          : rows.every(
                (r) =>
                  r.status === "excluded" ||
                  r.cost_arrangement === "charged_elsewhere",
              )
            ? "Excluded from scope"
            : issues.length
              ? "Needs review"
              : "Documented input",
    };
  });
}
export function capitalChecks(project: AssessmentRequest) {
  const rows = (project.study?.cost_items ?? []).filter(
    (i) => i.cost_type === "capex",
  );
  return rows.flatMap((item) =>
    capitalRowIssues(item, project).map((message) => ({
      item,
      message,
      href: `/capex/${capitalGroup(item) === "unclassified" ? "validation" : capitalGroup(item)}#capital-${encodeURIComponent(item.item_id)}`,
    })),
  );
}
