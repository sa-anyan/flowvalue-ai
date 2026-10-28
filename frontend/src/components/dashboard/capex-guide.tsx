"use client";
import Link from "next/link";
import { ArrowUpRight, ClipboardList, Plus } from "lucide-react";
import type { AssessmentRequest } from "@/lib/assessment";
import {
  capitalCoverage,
  capitalChecks,
  capitalGroupLabels,
} from "@/lib/capex-analysis";
import { newCostItem, newStudy } from "@/lib/study";

export function CapexGuide({
  project,
  onProject,
  detailed = false,
}: {
  project: AssessmentRequest;
  onProject: (p: AssessmentRequest) => void;
  detailed?: boolean;
}) {
  const coverage = capitalCoverage(project);
  const checks = capitalChecks(project);
  const absent = coverage.filter((c) => !c.rows.length);
  const cases = project.study?.engineering_cases ?? [];
  const unpriced = cases.filter(
    (c) => !project.costing.equipment.some((e) => e.unit_id === c.unit_id),
  );
  const sourceGaps = checks.filter((c) => c.message.startsWith("Link a"));
  function add(code?: string) {
    const study = project.study ?? newStudy();
    const missing = coverage.filter(
      (c) => !c.rows.length && (!code || c.scope.code === code),
    );
    const space = Math.max(0, 500 - study.cost_items.length);
    const additions = missing.slice(0, space).map(({ scope }) => ({
      ...newCostItem("CAP-" + crypto.randomUUID(), "capex"),
      description: scope.label,
      category: capitalGroupLabels[scope.group] + " / " + scope.label,
      basis: "",
    }));
    if (additions.length)
      onProject({
        ...project,
        study: { ...study, cost_items: [...study.cost_items, ...additions] },
      });
  }
  return (
    <section
      className="panel capital-guide"
      aria-label="Capital estimate worklist"
    >
      <div className="panel-heading">
        <div>
          <span className="capex-kicker">ESTIMATE WORKLIST</span>
          <h3>What needs attention?</h3>
          <p>
            Specific next steps from this project’s equipment, cost scope and
            evidence.
          </p>
        </div>
        <ClipboardList size={20} />
      </div>
      <div className="capital-progress-grid">
        <div>
          <span>Equipment basis</span>
          <strong>{project.costing.equipment.length} priced entries</strong>
          <small>
            {unpriced.length
              ? `${unpriced.length} investigation units remain unpriced`
              : "Reconcile against the design equipment list"}
          </small>
        </div>
        <div>
          <span>Scope register</span>
          <strong>
            {coverage.filter((c) => c.rows.length).length} of {coverage.length}{" "}
            areas recorded
          </strong>
          <small>
            {absent.length} not listed ·{" "}
            {coverage.filter((c) => c.status === "Needs review").length} need
            review
          </small>
        </div>
        <div>
          <span>Cost traceability</span>
          <strong>{sourceGaps.length} source gaps</strong>
          <small>Linked sources still require an applicability review</small>
        </div>
      </div>
      <div className="capital-next-actions">
        {!project.study?.design_basis.location && (
          <Link href="/capex/assumptions">
            Establish location and site basis <ArrowUpRight size={14} />
          </Link>
        )}
        {unpriced.length > 0 && (
          <Link href="/capex/equipment#engineering-analyst">
            Complete sizing or quotation for {unpriced.length} unpriced units{" "}
            <ArrowUpRight size={14} />
          </Link>
        )}
        {checks.slice(0, 3).map((check, i) => (
          <Link key={check.item.item_id + i} href={check.href}>
            <span>
              <strong>{check.item.description}</strong>
              {check.message}
            </span>
            <ArrowUpRight size={14} />
          </Link>
        ))}
        {!checks.length && !absent.length && (
          <p>
            Scope entries are documented. Reconcile technical suitability and
            the complete investment boundary before issuing an estimate.
          </p>
        )}
      </div>
      {absent.length > 0 && (
        <div className="capital-checklist-action">
          <div>
            <strong>
              {absent.length} capital scope areas are not assessed
            </strong>
            <p>
              Create named, unpriced rows to record costs or justified
              exclusions. Existing entries remain in place.
            </p>
          </div>
          <button
            className="capex-action-button"
            disabled={(project.study?.cost_items.length ?? 0) >= 500}
            onClick={() => add()}
          >
            <Plus size={15} />
            Create missing scope rows
          </button>
        </div>
      )}
      {detailed && (
        <div className="table-scroll">
          <table className="capex-breakdown-table">
            <thead>
              <tr>
                <th>Scope</th>
                <th>Work package</th>
                <th>Review state</th>
                <th>Next step</th>
              </tr>
            </thead>
            <tbody>
              {coverage.map(({ scope, rows, status }) => (
                <tr key={scope.code}>
                  <td>{scope.code}</td>
                  <td>
                    <strong>{scope.label}</strong>
                    <small className="capital-row-help">{scope.prompt}</small>
                  </td>
                  <td>{status}</td>
                  <td>
                    {rows.length ? (
                      <Link
                        className="capex-text-link"
                        href={`/capex/${scope.group}#capital-${encodeURIComponent(rows[0].item_id)}`}
                      >
                        Review entries <ArrowUpRight size={13} />
                      </Link>
                    ) : (
                      <button
                        className="capex-text-link"
                        disabled={
                          (project.study?.cost_items.length ?? 0) >= 500
                        }
                        onClick={() => add(scope.code)}
                      >
                        Add scope row
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="capex-caption">
        Scope coverage is a record count, not an estimate-accuracy rating. The
        financial model still uses equipment bare-module CAPEX.
      </p>
    </section>
  );
}

export function CapexEquipmentBasis({
  project,
}: {
  project: AssessmentRequest;
}) {
  const cases = project.study?.engineering_cases ?? [];
  return (
    <section className="panel capital-equipment-basis">
      <div>
        <span className="capex-kicker">FROM DESIGN TO ESTIMATE</span>
        <h3>Equipment requirements and pricing basis</h3>
        <p>
          Each tag should link to a duty, sizing input and quotation or
          supported correlation. A stream table alone does not establish a
          complete plant cost.
        </p>
      </div>
      <div className="capital-equipment-counts">
        <span>
          <strong>{project.costing.equipment.length}</strong> priced entries
        </span>
        <span>
          <strong>{cases.length}</strong> service investigations
        </span>
      </div>
      <Link className="capex-text-link" href="/capex/assumptions">
        Review cost-year, currency and sources <ArrowUpRight size={14} />
      </Link>
    </section>
  );
}
