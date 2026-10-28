"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/client-api";
import {
  apiError,
  usd,
  type AssessmentRequest,
  type Stream,
} from "@/lib/assessment";
import {
  costTypes,
  newCostItem,
  newStudy,
  type CostItem,
  type CostType,
  type Evidence,
  type Study,
  type StudyReview,
} from "@/lib/study";

function downloadJson(value: unknown, name: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
export function StudyWorkspace({
  mode = "study",
  project,
  onProject,
  streams,
}: {
  mode?: "study" | "capex" | "opex";
  project: AssessmentRequest;
  streams: Stream[];
  onProject: (p: AssessmentRequest) => void;
}) {
  const latestProject = useRef(project);
  useEffect(() => {
    latestProject.current = project;
  }, [project]);
  const study = project.study ?? newStudy();
  const signature = JSON.stringify(study);
  const [response, setResponse] = useState<{
    signature: string;
    data?: StudyReview;
    error?: string;
  } | null>(null);
  const [reviewer, setReviewer] = useState("");
  const projectSignature = JSON.stringify(project);
  const [confirmedSignature, setConfirmedSignature] = useState<string | null>(
    null,
  );
  const confirm = confirmedSignature === projectSignature;
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [evidenceDraft, setEvidenceDraft] = useState({
    title: "",
    reference: "",
    source_url: "",
    observed_on: "",
    kind: "assumption" as Evidence["kind"],
    reviewer: "",
    limitation: "",
  });
  const [newType, setNewType] = useState<CostType>(
    mode === "capex" ? "capex" : "fixed_opex",
  );
  const [newDescription, setNewDescription] = useState("");
  const costOptions = Object.entries(costTypes).filter(([key]) =>
    mode === "capex" ? key === "capex" : key !== "capex",
  );
  const visibleItems = study.cost_items.filter((item) =>
    mode === "capex" ? item.cost_type === "capex" : item.cost_type !== "capex",
  );
  const current = response?.signature === signature ? response : null;
  const review = current?.data;
  useEffect(() => {
    if (!project.study) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      apiFetch("/api/study/review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: signature,
        signal: controller.signal,
      })
        .then(async (r) => {
          if (!r.ok) throw Error(await apiError(r));
          return r.json() as Promise<StudyReview>;
        })
        .then((data) => setResponse({ signature, data }))
        .catch((e) => {
          if (e.name !== "AbortError")
            setResponse({ signature, error: e.message });
        });
    }, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [signature, project.study]);
  function edit(value: Study) {
    setConfirmedSignature(null);
    setMessage("");
    onProject({ ...project, study: value });
  }
  function itemChange(id: string, change: Partial<CostItem>) {
    edit({
      ...study,
      cost_items: study.cost_items.map((i) =>
        i.item_id === id ? { ...i, ...change } : i,
      ),
    });
  }
  async function apply() {
    setBusy(true);
    setMessage("");
    try {
      const r = await apiFetch("/api/study/apply-opex", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project, reviewer, confirm_replace: confirm }),
      });
      if (!r.ok) throw Error(await apiError(r));
      const applied = await r.json();
      if (JSON.stringify(latestProject.current) !== JSON.stringify(project))
        throw Error(
          "Project changed while applying OPEX. Current edits were retained; review and apply again.",
        );
      onProject(applied);
      setConfirmedSignature(null);
      setMessage(
        "Reviewed OPEX snapshot applied. The financial playground now uses these base costs; save a cloud revision to retain this decision.",
      );
    } catch (e) {
      setMessage(
        e instanceof Error
          ? e.message
          : "Could not apply OPEX; current model retained.",
      );
    } finally {
      setBusy(false);
    }
  }
  function addEvidence() {
    if (!evidenceDraft.title.trim()) {
      setMessage("Provide an evidence title.");
      return;
    }
    let url: string | null = null;
    if (evidenceDraft.source_url.trim()) {
      try {
        const parsed = new URL(evidenceDraft.source_url);
        if (!["http:", "https:"].includes(parsed.protocol)) throw Error();
        url = parsed.href;
      } catch {
        setMessage("Evidence source must be a valid HTTP(S) URL.");
        return;
      }
    }
    const record: Evidence = {
      ...evidenceDraft,
      evidence_id: `EV-${crypto.randomUUID()}`,
      source_url: url,
      observed_on: evidenceDraft.observed_on || null,
    };
    edit({ ...study, evidence: [...study.evidence, record] });
    setEvidenceDraft({
      title: "",
      reference: "",
      source_url: "",
      observed_on: "",
      kind: "assumption",
      reviewer: "",
      limitation: "",
    });
  }
  return (
    <section
      id="study"
      className="panel extension-panel study-workspace"
      aria-label="Study design basis and cost ledger"
    >
      <h2>
        {mode === "study"
          ? "Design basis & evidence"
          : mode === "capex"
            ? "Capital cost register"
            : "Operating cost register"}
      </h2>
      <p>
        {mode === "study"
          ? "Define the process, requirements and evidence used throughout this project."
          : mode === "capex"
            ? "Record capital scope and estimates. These planning entries are separate from the equipment BOM and are not added to financial CAPEX."
            : "Build fixed and variable operating budgets, then explicitly review and apply their annual totals."}
      </p>
      {mode !== "study" && (
        <p>
          <Link href="/dashboard">
            Manage shared design requirements and evidence in Study setup ↗
          </Link>
        </p>
      )}

      {!project.study ? (
        <Button onClick={() => edit(newStudy())}>Start study register</Button>
      ) : (
        <>
          <div className="extension-actions">
            <Button
              variant="outline"
              onClick={() =>
                downloadJson(
                  { ...project, streams },
                  "flowvalue-study-project.json",
                )
              }
            >
              Download study project JSON
            </Button>
            <Button
              variant="outline"
              disabled={!review}
              onClick={() =>
                downloadJson(
                  {
                    schema_version: "flowvalue-study-review-v1",
                    project,
                    review,
                    generated_at: new Date().toISOString(),
                    recognition_status:
                      "Not accredited; user-input review only",
                  },
                  "flowvalue-study-review.json",
                )
              }
            >
              Download study review record
            </Button>
          </div>
          {mode === "study" && (
            <>
              <details open>
                <summary>Design basis & requirements</summary>
                <label className="extension-full-label">
                  Process description
                  <textarea
                    aria-label="Study process description"
                    maxLength={10000}
                    value={study.design_basis.description}
                    onChange={(e) =>
                      edit({
                        ...study,
                        design_basis: {
                          ...study.design_basis,
                          description: e.target.value,
                        },
                      })
                    }
                  />
                </label>
                <div className="extension-actions">
                  <label>
                    Product specification
                    <input
                      aria-label="Study product specification"
                      maxLength={3000}
                      value={study.design_basis.product_specification}
                      onChange={(e) =>
                        edit({
                          ...study,
                          design_basis: {
                            ...study.design_basis,
                            product_specification: e.target.value,
                          },
                        })
                      }
                    />
                  </label>
                  <label>
                    Site location
                    <input
                      aria-label="Study site location"
                      maxLength={300}
                      value={study.design_basis.location}
                      onChange={(e) =>
                        edit({
                          ...study,
                          design_basis: {
                            ...study.design_basis,
                            location: e.target.value,
                          },
                        })
                      }
                    />
                  </label>
                  <label>
                    Site type
                    <select
                      aria-label="Study site type"
                      value={study.design_basis.site_type}
                      onChange={(e) =>
                        edit({
                          ...study,
                          design_basis: {
                            ...study.design_basis,
                            site_type: e.target
                              .value as Study["design_basis"]["site_type"],
                          },
                        })
                      }
                    >
                      <option value="unknown">Not established</option>
                      <option value="greenfield">Greenfield</option>
                      <option value="integrated">
                        Integrated with existing plant
                      </option>
                      <option value="brownfield">Brownfield</option>
                    </select>
                  </label>
                  <label>
                    Operating hours/year
                    <input
                      aria-label="Study operating hours"
                      type="number"
                      min={1}
                      max={8784}
                      value={study.design_basis.operating_hours_per_year ?? ""}
                      onChange={(e) =>
                        edit({
                          ...study,
                          design_basis: {
                            ...study.design_basis,
                            operating_hours_per_year:
                              e.target.value === ""
                                ? null
                                : Number(e.target.value),
                          },
                        })
                      }
                    />
                  </label>
                </div>
                {(
                  [
                    [
                      "requirements",
                      "Service, material, hygiene & other design requirements",
                    ],
                    [
                      "source_context",
                      "Balance / simulation / design source references",
                    ],
                    [
                      "unresolved_questions",
                      "Unresolved questions & assumptions",
                    ],
                  ] as const
                ).map(([key, label]) => (
                  <label key={key} className="extension-full-label">
                    {label}
                    <textarea
                      aria-label={label}
                      maxLength={5000}
                      value={study.design_basis[key]}
                      onChange={(e) =>
                        edit({
                          ...study,
                          design_basis: {
                            ...study.design_basis,
                            [key]: e.target.value,
                          },
                        })
                      }
                    />
                  </label>
                ))}
              </details>
              <details>
                <summary>
                  Evidence & assumption register · {study.evidence.length}
                </summary>
                <p>
                  References and reviewer names are user-supplied. Linking a
                  source does not independently verify its applicability.
                  Assumptions remain labelled as assumptions.
                </p>
                {study.evidence.map((e) => (
                  <div className="study-evidence" key={e.evidence_id}>
                    <strong>{e.title}</strong>
                    <p>
                      {e.kind} · {e.reference} · reviewer{" "}
                      {e.reviewer || "not recorded"}
                    </p>
                    {e.source_url && (
                      <a href={e.source_url} target="_blank" rel="noreferrer">
                        Source ↗
                      </a>
                    )}
                    <p>{e.limitation}</p>
                    <Button
                      variant="outline"
                      disabled={
                        study.cost_items.some((i) =>
                          i.evidence_ids.includes(e.evidence_id),
                        ) ||
                        !!study.engineering_cases?.some((c) =>
                          c.evidence_ids.includes(e.evidence_id),
                        )
                      }
                      onClick={() =>
                        edit({
                          ...study,
                          evidence: study.evidence.filter(
                            (x) => x.evidence_id !== e.evidence_id,
                          ),
                        })
                      }
                    >
                      Remove evidence {e.title}
                    </Button>
                  </div>
                ))}
                <div className="extension-actions">
                  <label>
                    Evidence title
                    <input
                      aria-label="New evidence title"
                      maxLength={300}
                      value={evidenceDraft.title}
                      onChange={(e) =>
                        setEvidenceDraft({
                          ...evidenceDraft,
                          title: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    Evidence type
                    <select
                      aria-label="New evidence type"
                      value={evidenceDraft.kind}
                      onChange={(e) =>
                        setEvidenceDraft({
                          ...evidenceDraft,
                          kind: e.target.value as Evidence["kind"],
                        })
                      }
                    >
                      {[
                        "assumption",
                        "publication",
                        "quotation",
                        "design_input",
                        "measurement",
                      ].map((k) => (
                        <option key={k} value={k}>
                          {k.replaceAll("_", " ")}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Source URL
                    <input
                      aria-label="New evidence URL"
                      type="url"
                      value={evidenceDraft.source_url}
                      onChange={(e) =>
                        setEvidenceDraft({
                          ...evidenceDraft,
                          source_url: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    Evidence observation date
                    <input
                      aria-label="New evidence observation date"
                      type="date"
                      value={evidenceDraft.observed_on}
                      onChange={(e) =>
                        setEvidenceDraft({
                          ...evidenceDraft,
                          observed_on: e.target.value,
                        })
                      }
                      onBlur={(e) => {
                        const value = e.currentTarget.value;
                        setEvidenceDraft((d) => ({ ...d, observed_on: value }));
                      }}
                    />
                  </label>
                  <label>
                    Evidence reviewer
                    <input
                      aria-label="New evidence reviewer"
                      maxLength={150}
                      value={evidenceDraft.reviewer}
                      onChange={(e) =>
                        setEvidenceDraft({
                          ...evidenceDraft,
                          reviewer: e.target.value,
                        })
                      }
                    />
                  </label>
                </div>
                <label className="extension-full-label">
                  Document/page/reference
                  <textarea
                    aria-label="New evidence reference"
                    maxLength={2000}
                    value={evidenceDraft.reference}
                    onChange={(e) =>
                      setEvidenceDraft({
                        ...evidenceDraft,
                        reference: e.target.value,
                      })
                    }
                  />
                </label>
                <label className="extension-full-label">
                  Evidence limitations
                  <textarea
                    aria-label="New evidence limitations"
                    maxLength={1500}
                    value={evidenceDraft.limitation}
                    onChange={(e) =>
                      setEvidenceDraft({
                        ...evidenceDraft,
                        limitation: e.target.value,
                      })
                    }
                  />
                </label>
                <Button
                  onClick={addEvidence}
                  disabled={study.evidence.length >= 200}
                >
                  Add evidence record
                </Button>
              </details>
            </>
          )}
          {mode !== "study" && (
            <>
              <details open>
                <summary>
                  {mode === "capex" ? "CAPEX" : "OPEX"} ledger ·{" "}
                  {visibleItems.length} items
                </summary>
                <p>
                  OPEX quantities must be annual at the selected utilization.
                  Amount = quantity × USD unit rate × allocation. CAPEX is
                  planning-only here and is not added to the equipment BOM.
                  Unknown and unsupported amounts stay explicit.
                </p>
                <div className="extension-actions">
                  <label>
                    New cost description
                    <input
                      aria-label="New study cost description"
                      maxLength={300}
                      value={newDescription}
                      onChange={(e) => setNewDescription(e.target.value)}
                    />
                  </label>
                  <label>
                    Cost class
                    <select
                      aria-label="New study cost class"
                      value={newType}
                      onChange={(e) => setNewType(e.target.value as CostType)}
                    >
                      {costOptions.map(([key, label]) => (
                        <option key={key} value={key}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <Button
                    disabled={
                      !newDescription.trim() || study.cost_items.length >= 500
                    }
                    onClick={() => {
                      edit({
                        ...study,
                        cost_items: [
                          ...study.cost_items,
                          {
                            ...newCostItem(
                              `COST-${crypto.randomUUID()}`,
                              newType,
                            ),
                            description: newDescription.trim(),
                          },
                        ],
                      });
                      setNewDescription("");
                    }}
                  >
                    Add cost item
                  </Button>
                </div>
                {visibleItems.map((item) => {
                  const row = review?.rows.find(
                    (x) => x.item_id === item.item_id,
                  );
                  return (
                    <details
                      key={item.item_id}
                      className="study-cost-item"
                      open
                    >
                      <summary>
                        {item.description} · {costTypes[item.cost_type]} ·{" "}
                        {item.status.replaceAll("_", " ")} ·{" "}
                        {row?.amount_usd == null
                          ? "unpriced"
                          : usd(row.amount_usd)}
                      </summary>
                      <div className="extension-actions">
                        <label className="extension-checkbox">
                          <input
                            type="checkbox"
                            aria-label={`Include ${item.description}`}
                            checked={item.status === "included"}
                            onChange={(e) =>
                              itemChange(item.item_id, {
                                status: e.target.checked
                                  ? "included"
                                  : "excluded",
                              })
                            }
                          />
                          Include cost
                        </label>
                        <label>
                          Status
                          <select
                            aria-label={`${item.description} status`}
                            value={item.status}
                            onChange={(e) =>
                              itemChange(item.item_id, {
                                status: e.target.value as CostItem["status"],
                              })
                            }
                          >
                            {[
                              "included",
                              "excluded",
                              "not_applicable",
                              "missing",
                              "unsupported",
                            ].map((k) => (
                              <option key={k} value={k}>
                                {k.replaceAll("_", " ")}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Category
                          <input
                            aria-label={`${item.description} category`}
                            maxLength={120}
                            value={item.category}
                            onChange={(e) =>
                              itemChange(item.item_id, {
                                category: e.target.value,
                              })
                            }
                          />
                        </label>
                        <label>
                          Cost class
                          <select
                            aria-label={`${item.description} cost class`}
                            value={item.cost_type}
                            onChange={(e) =>
                              itemChange(item.item_id, {
                                cost_type: e.target.value as CostType,
                              })
                            }
                          >
                            {costOptions.map(([key, label]) => (
                              <option key={key} value={key}>
                                {label}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Quantity
                          <input
                            aria-label={`${item.description} quantity`}
                            type="number"
                            min={0}
                            step="any"
                            value={item.quantity ?? ""}
                            onChange={(e) =>
                              itemChange(item.item_id, {
                                quantity:
                                  e.target.value === ""
                                    ? null
                                    : Number(e.target.value),
                              })
                            }
                          />
                        </label>
                        <label>
                          Quantity unit
                          <input
                            aria-label={`${item.description} unit`}
                            maxLength={80}
                            value={item.unit}
                            onChange={(e) =>
                              itemChange(item.item_id, { unit: e.target.value })
                            }
                          />
                        </label>
                        <label>
                          USD / quantity unit
                          <input
                            aria-label={`${item.description} rate`}
                            type="number"
                            min={0}
                            step="any"
                            value={item.rate_usd ?? ""}
                            onChange={(e) =>
                              itemChange(item.item_id, {
                                rate_usd:
                                  e.target.value === ""
                                    ? null
                                    : Number(e.target.value),
                              })
                            }
                          />
                        </label>
                        <label>
                          Allocation (0–1)
                          <input
                            aria-label={`${item.description} allocation`}
                            type="number"
                            min={0}
                            max={1}
                            step={0.01}
                            value={item.allocation_fraction}
                            onChange={(e) =>
                              itemChange(item.item_id, {
                                allocation_fraction: Number(e.target.value),
                              })
                            }
                          />
                        </label>
                        <label>
                          Employment / cost allocation
                          <select
                            aria-label={`${item.description} arrangement`}
                            value={item.cost_arrangement}
                            onChange={(e) =>
                              itemChange(item.item_id, {
                                cost_arrangement: e.target
                                  .value as CostItem["cost_arrangement"],
                              })
                            }
                          >
                            <option value="incremental">
                              Incremental / new expenditure
                            </option>
                            <option value="allocated_existing">
                              Allocated existing resource
                            </option>
                            <option value="charged_elsewhere">
                              Already charged elsewhere
                            </option>
                          </select>
                        </label>
                      </div>
                      <label className="extension-full-label">
                        Inclusion / exclusion and calculation basis
                        <textarea
                          aria-label={`${item.description} basis`}
                          maxLength={2000}
                          value={item.basis}
                          onChange={(e) =>
                            itemChange(item.item_id, { basis: e.target.value })
                          }
                        />
                      </label>
                      {study.evidence.length > 0 && (
                        <fieldset>
                          <legend>Linked evidence</legend>
                          {study.evidence.map((e) => (
                            <label
                              className="extension-checkbox"
                              key={e.evidence_id}
                            >
                              <input
                                type="checkbox"
                                checked={item.evidence_ids.includes(
                                  e.evidence_id,
                                )}
                                onChange={(v) =>
                                  itemChange(item.item_id, {
                                    evidence_ids: v.target.checked
                                      ? [...item.evidence_ids, e.evidence_id]
                                      : item.evidence_ids.filter(
                                          (id) => id !== e.evidence_id,
                                        ),
                                  })
                                }
                              />
                              {e.title}
                            </label>
                          ))}
                        </fieldset>
                      )}
                      {row?.issues.map((issue) => (
                        <p key={issue}>{issue}</p>
                      ))}
                      <Button
                        variant="outline"
                        onClick={() =>
                          edit({
                            ...study,
                            cost_items: study.cost_items.filter(
                              (x) => x.item_id !== item.item_id,
                            ),
                          })
                        }
                      >
                        Remove cost {item.description}
                      </Button>
                    </details>
                  );
                })}
              </details>
            </>
          )}
          <div role="status">
            {current?.error || (!review ? "Checking study inputs…" : "")}
          </div>
          {review && mode === "opex" && (
            <>
              <h3>Coverage & cost review</h3>
              <div className="study-totals">
                {costOptions.map(([key, label]) => (
                  <p key={key}>
                    <strong>{label}</strong>
                    <br />
                    {usd(review.totals_usd[key as CostType])}
                    {key !== "capex" ? "/year" : ""}
                  </p>
                ))}
              </div>
              <p>
                Totals count only included, sufficiently specified entries; zero
                is not a completeness claim. FCOP is fixed OPEX. VCOP is
                feedstock + utilities + other variable OPEX.
              </p>
              <ul>
                {review.questions.map((q) => (
                  <li key={q}>{q}</li>
                ))}
                {review.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
                {review.opex_application_blockers.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
              <p>{review.notice}</p>
              {study.application ? (
                <p>
                  <strong>
                    {review.application_current
                      ? "Ledger matches last application."
                      : "Application stale — study or evidence changed. Reapply after review."}
                  </strong>{" "}
                  Last applied by {study.application.reviewer} on{" "}
                  {study.application.applied_on}. Manual financial edits and
                  sensitivity controls can change the applied snapshot.
                </p>
              ) : (
                <p>
                  Ledger OPEX has not been applied. Financial results still use
                  current manual inputs.
                </p>
              )}
            </>
          )}
          {mode === "opex" && (
            <>
              <div className="extension-actions">
                <label>
                  OPEX reviewer
                  <input
                    aria-label="Study OPEX reviewer"
                    maxLength={150}
                    value={reviewer}
                    onChange={(e) => {
                      setReviewer(e.target.value);
                      setConfirmedSignature(null);
                    }}
                  />
                </label>
              </div>
              <label className="extension-checkbox">
                <input
                  aria-label="Confirm OPEX replacement"
                  type="checkbox"
                  checked={confirm}
                  onChange={(e) =>
                    setConfirmedSignature(
                      e.target.checked ? projectSignature : null,
                    )
                  }
                />
                I reviewed annual amounts and allocations. Replace all base
                fixed/variable OPEX, including feedstock/utilities, and clear
                conflicting detailed advisor allocations.
              </label>
              <Button
                onClick={apply}
                disabled={
                  busy ||
                  !review?.can_apply_opex ||
                  !confirm ||
                  !reviewer.trim()
                }
              >
                {busy ? "Applying…" : "Apply reviewed OPEX to financial model"}
              </Button>
            </>
          )}
          <p role="status">{message}</p>
          <p>
            Study registers are saved with project revisions. This is not an
            accreditation assessment or an IChemE-endorsed workflow.
          </p>
        </>
      )}
    </section>
  );
}
