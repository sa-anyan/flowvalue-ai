"use client";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/client-api";
import {
  apiError,
  defaults,
  fieldLabels,
  kindLabels,
  usd,
  type AssessmentRequest,
  type Kind,
} from "@/lib/assessment";
import { newStudy } from "@/lib/study";
import {
  materials,
  newEngineeringCase,
  type EngineeringCase,
  type EngineeringResearch,
  type UnitReport,
  type UnitService,
} from "@/lib/engineering";
import type { NativeImport } from "@/lib/workspace";

const defaultKeys = new Set([
  "height_diameter_ratio",
  "allowable_stress_mpa",
  "weld_efficiency",
  "corrosion_allowance_mm",
  "minimum_thickness_mm",
  "lmtd_correction_factor",
  "efficiency",
  "isentropic_efficiency",
  "heat_capacity_ratio",
  "reference_cepci",
]);
const kinds: EngineeringCase["unit_kind"][] = [
  "heat_exchanger",
  "vessel",
  "reactor",
  "pump",
  "compressor",
  "valve",
  "other",
];
const textFields: [keyof UnitService, string, number][] = [
  ["duty_description", "Equipment duty / service", 1500],
  ["fluid_composition", "Process chemistry / composition", 2000],
  [
    "concentration_basis",
    "Concentrations, impurities and composition basis",
    1000,
  ],
  ["corrosion_conditions", "Corrosion, erosion, solids and service life", 1500],
  [
    "cleaning_regime",
    "Cleaning, sanitization and sterilization conditions",
    1500,
  ],
  [
    "lining_or_cladding",
    "Lining / cladding / internal-external construction",
    1000,
  ],
  [
    "material_rationale",
    "Material-selection reasoning and evidence applicability",
    2500,
  ],
];
function download(value: unknown, name: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
export function EngineeringAnalyst({
  project,
  onProject,
  native,
  aiAvailable,
  selectedUnit,
}: {
  project: AssessmentRequest;
  onProject: (p: AssessmentRequest) => void;
  native?: NativeImport | null;
  aiAvailable: boolean;
  selectedUnit?: string;
}) {
  const ids = Array.from(
    new Set([
      ...project.costing.equipment.map((e) => e.unit_id),
      ...(project.study?.engineering_cases || []).map((e) => e.unit_id),
      ...(native?.units || []).map((u) => u.unit_id),
    ]),
  );
  const [selected, setSelected] = useState(ids[0] || "");
  const [newId, setNewId] = useState("");
  const [newKind, setNewKind] = useState<EngineeringCase["unit_kind"]>("valve");
  const unitId = selectedUnit || selected;
  function start(id: string, kind?: EngineeringCase["unit_kind"]) {
    if (!id.trim() || id.length > 100) return;
    const study = project.study ?? newStudy();
    if (study.engineering_cases?.some((c) => c.unit_id === id)) {
      setSelected(id);
      return;
    }
    const existing = project.costing.equipment.find((e) => e.unit_id === id);
    const k =
      kind ||
      (existing && existing.kind !== "quoted" ? existing.kind : "other");
    onProject({
      ...project,
      study: {
        ...study,
        engineering_cases: [
          ...(study.engineering_cases || []),
          newEngineeringCase(id, k, existing),
        ],
      },
    });
    setSelected(id);
    setNewId("");
  }
  return (
    <section
      className="panel extension-panel"
      id={selectedUnit ? undefined : "engineering-analyst"}
      aria-label="Engineering analyst"
    >
      <h2>Engineering analyst · unit investigation</h2>
      <p>
        Investigate service constraints, materials and sizing before reviewing a
        preliminary baseline. Rule checks use no paid AI calls. Grades, linings
        and external shells are distinct; no material name establishes
        compatibility or sterility.
      </p>
      {!selectedUnit && (
        <div className="extension-actions">
          <label>
            Unit to investigate
            <select
              aria-label="Engineering unit"
              value={unitId}
              onChange={(e) => setSelected(e.target.value)}
            >
              <option value="">Choose a unit</option>
              {ids.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
          </label>
          <a href="/process-flow">Inspect connected 2D/3D process ↗</a>
          <a href="/engineering-review">Saved-revision peer review centre ↗</a>
        </div>
      )}
      {!selectedUnit && (
        <details>
          <summary>Add an unpriced unit investigation</summary>
          <p>
            Valves and other unsupported equipment stay unpriced until a
            reviewed quotation or supported model is supplied.
          </p>
          <div className="extension-actions">
            <label>
              Unit ID
              <input
                aria-label="New engineering unit ID"
                maxLength={100}
                value={newId}
                onChange={(e) => setNewId(e.target.value)}
              />
            </label>
            <label>
              Equipment service
              <select
                aria-label="New engineering unit kind"
                value={newKind}
                onChange={(e) =>
                  setNewKind(e.target.value as EngineeringCase["unit_kind"])
                }
              >
                {kinds.map((k) => (
                  <option key={k} value={k}>
                    {k.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </label>
            <Button
              disabled={!newId.trim() || ids.includes(newId.trim())}
              onClick={() => start(newId.trim(), newKind)}
            >
              Add unit investigation
            </Button>
          </div>
        </details>
      )}
      {unitId &&
      !project.study?.engineering_cases?.some((c) => c.unit_id === unitId) ? (
        <Button onClick={() => start(unitId)}>
          Start investigation for {unitId}
        </Button>
      ) : unitId ? (
        <UnitInvestigation
          key={unitId}
          unitId={unitId}
          project={project}
          onProject={onProject}
          aiAvailable={aiAvailable}
        />
      ) : (
        <p>Choose an equipment item or add an unpriced investigation.</p>
      )}
    </section>
  );
}
function UnitInvestigation({
  unitId,
  project,
  onProject,
  aiAvailable,
}: {
  unitId: string;
  project: AssessmentRequest;
  onProject: (p: AssessmentRequest) => void;
  aiAvailable: boolean;
}) {
  const study = project.study!;
  const investigation = study.engineering_cases!.find(
    (c) => c.unit_id === unitId,
  )!;
  const signature = JSON.stringify({ project, unit_id: unitId });
  const latest = useRef(signature);
  useEffect(() => {
    latest.current = signature;
  }, [signature]);
  const [response, setResponse] = useState<{
    signature: string;
    data?: UnitReport;
    error?: string;
  } | null>(null);
  const [reviewer, setReviewer] = useState("");
  const [basis, setBasis] = useState("");
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [research, setResearch] = useState<{
    signature: string;
    data: EngineeringResearch;
  } | null>(null);
  const current = response?.signature === signature ? response : null;
  const report = current?.data;
  useEffect(() => {
    const controller = new AbortController();
    const t = setTimeout(() => {
      apiFetch("/api/engineering/investigate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: signature,
        signal: controller.signal,
      })
        .then(async (r) => {
          if (!r.ok) throw Error(await apiError(r));
          return r.json() as Promise<UnitReport>;
        })
        .then((data) => setResponse({ signature, data }))
        .catch((e) => {
          if (e.name !== "AbortError")
            setResponse({ signature, error: e.message });
        });
    }, 350);
    return () => {
      clearTimeout(t);
      controller.abort();
    };
  }, [signature]);
  function edit(change: Partial<EngineeringCase>, reviewToggle = false) {
    const updated = { ...investigation, ...change };
    if (!reviewToggle)
      updated.service = {
        ...updated.service,
        compatibility_reviewed: false,
        mechanical_scope_reviewed: false,
      };
    onProject({
      ...project,
      study: {
        ...study,
        engineering_cases: study.engineering_cases!.map((c) =>
          c.unit_id === unitId ? updated : c,
        ),
      },
    });
    setConfirmation(null);
    setMessage("");
  }
  function service(change: Partial<UnitService>, toggle = false) {
    edit({ service: { ...investigation.service, ...change } }, toggle);
  }
  const proposal: Record<string, number | string> = Object.keys(
    investigation.proposed_equipment,
  ).length
    ? investigation.proposed_equipment
    : {
        kind: "quoted",
        unit_id: unitId,
        quantity: 1,
        material: "carbon_steel",
        reference_cepci: project.costing.settings.cepci_current,
        source: "",
      };
  const modelKind = (
    typeof proposal.kind === "string" && proposal.kind in kindLabels
      ? proposal.kind
      : "quoted"
  ) as Kind;
  function setModel(k: Kind) {
    edit({
      proposed_equipment: {
        kind: k,
        unit_id: unitId,
        quantity: 1,
        material: "carbon_steel",
        ...Object.fromEntries(
          Object.entries(defaults[k]).map(([key, value]) => [
            key,
            defaultKeys.has(key) ? value : "",
          ]),
        ),
        ...(k === "quoted" ? { source: "" } : {}),
      },
    });
  }
  function addSource(source: {
    title: string;
    url: string;
    scope: string;
    reviewed_on: string;
  }) {
    const existing = study.evidence.find((e) => e.source_url === source.url);
    const id = existing?.evidence_id || `ENG-${crypto.randomUUID()}`;
    const e = existing || {
      evidence_id: id,
      title: source.title,
      kind: "publication" as const,
      source_url: source.url,
      reference: source.scope,
      observed_on: source.reviewed_on,
      reviewer: "FlowValue source catalog; user must review applicability",
      limitation:
        "General guidance only. No actual-service compatibility has been verified.",
    };
    const updated = {
      ...investigation,
      evidence_ids: Array.from(new Set([...investigation.evidence_ids, id])),
      service: {
        ...investigation.service,
        compatibility_reviewed: false,
        mechanical_scope_reviewed: false,
      },
    };
    onProject({
      ...project,
      study: {
        ...study,
        evidence: existing ? study.evidence : [...study.evidence, e],
        engineering_cases: study.engineering_cases!.map((c) =>
          c.unit_id === unitId ? updated : c,
        ),
      },
    });
    setConfirmation(null);
  }
  async function apply() {
    setBusy("apply");
    setMessage("");
    try {
      let reviewVersion: string | undefined;
      try {
        reviewVersion = JSON.parse(
          sessionStorage.getItem("flowvalue-project-reference") || "null",
        )?.current?.version_id;
      } catch {}
      const r = await apiFetch("/api/engineering/apply-baseline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project,
          unit_id: unitId,
          reviewer,
          basis,
          confirm: confirmation === signature,
          review_version_id: reviewVersion,
        }),
      });
      if (!r.ok) throw Error(await apiError(r));
      const updated = await r.json();
      if (latest.current !== signature)
        throw Error(
          "Project changed during review. Current edits retained; review again.",
        );
      onProject(updated);
      setConfirmation(null);
      setMessage(
        "Preliminary unit baseline applied. Save a cloud revision to preserve the record. This is not independent engineering certification.",
      );
    } catch (e) {
      setMessage(
        e instanceof Error
          ? e.message
          : "Baseline could not be applied; current equipment retained.",
      );
    } finally {
      setBusy("");
    }
  }
  async function runResearch() {
    setBusy("research");
    setMessage("");
    try {
      const r = await apiFetch("/api/engineering/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: signature,
      });
      if (!r.ok) throw Error(await apiError(r));
      setResearch({ signature, data: await r.json() });
    } catch (e) {
      setMessage(
        e instanceof Error
          ? e.message
          : "Research unavailable; current design retained.",
      );
    } finally {
      setBusy("");
    }
  }
  return (
    <div>
      <h3>
        {unitId} ·{" "}
        {report?.baseline_status.replaceAll("_", " ") || "investigation draft"}
      </h3>
      <p>
        Changing service, evidence or sizing resets the review checkboxes.
        Previous baselines remain in history. Changes elsewhere in the
        BOM/design basis can also make a stored baseline stale.
      </p>
      <div className="extension-actions">
        <label>
          Equipment service
          <select
            aria-label={`${unitId} investigation kind`}
            value={investigation.unit_kind}
            onChange={(e) =>
              edit({
                unit_kind: e.target.value as EngineeringCase["unit_kind"],
              })
            }
          >
            {kinds.map((k) => (
              <option key={k} value={k}>
                {k.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </label>
        <label>
          Phase
          <select
            aria-label={`${unitId} service phase`}
            value={investigation.service.phase}
            onChange={(e) =>
              service({ phase: e.target.value as UnitService["phase"] })
            }
          >
            {["unknown", "liquid", "gas", "multiphase", "solid"].map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </label>
        <label>
          Food-contact service
          <select
            aria-label={`${unitId} food contact`}
            value={
              investigation.service.food_contact === null
                ? "unknown"
                : String(investigation.service.food_contact)
            }
            onChange={(e) =>
              service({
                food_contact:
                  e.target.value === "unknown"
                    ? null
                    : e.target.value === "true",
              })
            }
          >
            <option value="unknown">Not established</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </label>
      </div>
      <details open>
        <summary>Service, chemistry and material investigation</summary>
        {textFields.map(([key, label, max]) => (
          <label className="extension-full-label" key={key}>
            {label}
            <textarea
              aria-label={`${unitId} ${key}`}
              maxLength={max}
              value={String(investigation.service[key] ?? "")}
              onChange={(e) => service({ [key]: e.target.value })}
            />
          </label>
        ))}
        <div className="extension-actions">
          {(
            [
              ["normal_temperature_c", "Normal temperature °C"],
              ["design_temperature_c", "Design temperature °C"],
              ["design_pressure_barg", "Design pressure barg"],
            ] as const
          ).map(([key, label]) => (
            <label key={key}>
              {label}
              <input
                aria-label={`${unitId} service ${key}`}
                type="number"
                step="any"
                value={investigation.service[key] ?? ""}
                onChange={(e) =>
                  service({
                    [key]:
                      e.target.value === "" ? null : Number(e.target.value),
                  })
                }
              />
            </label>
          ))}
          {(
            [
              ["wetted_material", "Wetted / internal material"],
              ["shell_material", "Structural / external material"],
            ] as const
          ).map(([key, label]) => (
            <label key={key}>
              {label}
              <select
                aria-label={`${unitId} ${key}`}
                value={investigation.service[key]}
                onChange={(e) => service({ [key]: e.target.value })}
              >
                {Object.entries(materials).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
        <label className="extension-full-label">
          Engineering hypothesis and investigation plan
          <textarea
            aria-label={`${unitId} hypothesis`}
            maxLength={2000}
            value={investigation.hypothesis}
            onChange={(e) => edit({ hypothesis: e.target.value })}
          />
        </label>
        <label className="extension-full-label">
          Counter-evidence, challenges and unresolved suitability
          <textarea
            aria-label={`${unitId} counter evidence`}
            maxLength={2000}
            value={investigation.counter_evidence}
            onChange={(e) => edit({ counter_evidence: e.target.value })}
          />
        </label>
      </details>
      <details>
        <summary>Sizing / quotation proposal</summary>
        <Button
          variant="outline"
          disabled={
            !project.costing.equipment.some((e) => e.unit_id === unitId)
          }
          onClick={() => {
            const e = project.costing.equipment.find(
              (e) => e.unit_id === unitId,
            )!;
            edit({
              proposed_equipment: Object.fromEntries(
                Object.entries(e).filter(
                  ([, v]) => typeof v === "number" || typeof v === "string",
                ),
              ) as Record<string, number | string>,
            });
          }}
        >
          Copy current BOM inputs into proposal
        </Button>
        <p>
          Numerical inputs are per unit. Supported models reuse the
          deterministic costing engine. Quoted assemblies are required for
          composite/lining or unsupported material costing. Blank process duties
          are not invented.
        </p>
        <div className="extension-actions">
          <label>
            Sizing model
            <select
              aria-label={`${unitId} sizing model`}
              value={modelKind}
              onChange={(e) => setModel(e.target.value as Kind)}
            >
              {Object.entries(kindLabels).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <label>
            Quantity
            <input
              aria-label={`${unitId} proposed quantity`}
              type="number"
              min={1}
              step={1}
              value={proposal.quantity ?? 1}
              onChange={(e) =>
                edit({
                  proposed_equipment: {
                    ...proposal,
                    quantity: Number(e.target.value),
                  },
                })
              }
            />
          </label>
          {modelKind !== "quoted" && (
            <label>
              Costing material proxy
              <select
                aria-label={`${unitId} costing material proxy`}
                value={proposal.material || "carbon_steel"}
                onChange={(e) =>
                  edit({
                    proposed_equipment: {
                      ...proposal,
                      material: e.target.value,
                    },
                  })
                }
              >
                <option value="carbon_steel">Carbon steel</option>
                <option value="stainless_steel">Generic stainless steel</option>
              </select>
            </label>
          )}
          {Object.keys(defaults[modelKind]).map((key) => (
            <label key={key}>
              {fieldLabels[key] || key.replaceAll("_", " ")}
              {defaultKeys.has(key) ? " (review default)" : ""}
              <input
                aria-label={`${unitId} proposed ${key}`}
                type="number"
                step="any"
                value={proposal[key] ?? ""}
                onChange={(e) =>
                  edit({
                    proposed_equipment: {
                      ...proposal,
                      [key]:
                        e.target.value === "" ? "" : Number(e.target.value),
                    },
                  })
                }
              />
            </label>
          ))}
        </div>
        {modelKind === "quoted" && (
          <label className="extension-full-label">
            Assembled-unit quotation / scope source
            <textarea
              aria-label={`${unitId} quote source`}
              maxLength={2000}
              value={String(proposal.source || "")}
              onChange={(e) =>
                edit({
                  proposed_equipment: { ...proposal, source: e.target.value },
                })
              }
            />
          </label>
        )}
      </details>
      <details>
        <summary>Linked evidence, sources and optional research</summary>
        <p>
          Public source links below are general guidance. Add project-specific
          sources in the study evidence register and explicitly review
          applicability. Neither an AI citation nor a checkbox certifies
          compatibility.
        </p>
        {study.evidence.map((e) => (
          <label className="extension-checkbox" key={e.evidence_id}>
            <input
              type="checkbox"
              checked={investigation.evidence_ids.includes(e.evidence_id)}
              onChange={(v) =>
                edit({
                  evidence_ids: v.target.checked
                    ? [...investigation.evidence_ids, e.evidence_id]
                    : investigation.evidence_ids.filter(
                        (id) => id !== e.evidence_id,
                      ),
                })
              }
            />
            {e.title} · {e.kind}
          </label>
        ))}
        {report?.sources.map((s) => (
          <div key={s.id}>
            <p>
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.title} ↗
              </a>{" "}
              · reviewed {s.reviewed_on}. {s.scope}
            </p>
            <Button
              variant="outline"
              disabled={study.evidence.length >= 200}
              onClick={() => addSource(s)}
            >
              Link source: {s.id}
            </Button>
          </div>
        ))}
        <p>
          Live unit research sends the selected service, hypothesis and a
          bounded design-context excerpt to OpenAI and searches primary sources.
          It incurs provider usage charges. No equipment or cost is changed.
        </p>
        <Button
          disabled={!aiAvailable || !!busy || !report}
          onClick={runResearch}
        >
          {busy === "research"
            ? "Researching selected unit…"
            : "Research this unit with sources"}
        </Button>
        {research && (
          <>
            <p>
              {research.signature === signature
                ? "Research for current inputs"
                : "Research is stale — unit or project inputs changed"}{" "}
              · {research.data.model} · {research.data.generated_at} ·{" "}
              {research.data.evidence_status}
            </p>
            <ReactMarkdown>{research.data.text}</ReactMarkdown>
            {research.data.citations.map((c, i) => (
              <p key={i}>
                <a href={c.url} target="_blank" rel="noreferrer">
                  {c.title || c.url}
                </a>
              </p>
            ))}
            <p>{research.data.notice}</p>
            <Button
              variant="outline"
              onClick={() =>
                download(research.data, `flowvalue-${unitId}-research.json`)
              }
            >
              Download research record
            </Button>
          </>
        )}
      </details>
      <div role="status">
        {current?.error || (!report ? "Reviewing unit inputs…" : "")}
      </div>
      {report && (
        <>
          <h3>Investigation priorities & material options</h3>
          <ol>
            {report.questions.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ol>
          {report.material_options.map((o) => (
            <p key={o.material}>
              <strong>{o.material}</strong>: {o.role}
            </p>
          ))}
          {report.sizing && (
            <p>
              Screening sizing:{" "}
              {Object.entries(report.sizing.sizing)
                .map(
                  ([k, v]) =>
                    `${k}: ${Number(v).toLocaleString(undefined, { maximumFractionDigits: 3 })}`,
                )
                .join(" · ")}
              <br />
              Purchased/unit {usd(report.sizing.purchased_equipment_cost_usd)} ·
              Bare module/unit {usd(report.sizing.bare_module_cost_usd)}
            </p>
          )}
          <ul>
            {report.blockers.map((b) => (
              <li key={b}>{b}</li>
            ))}
            {report.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
          <p>{report.notice}</p>
          <Button
            variant="outline"
            onClick={() =>
              download(report, `flowvalue-${unitId}-investigation.json`)
            }
          >
            Download unit investigation
          </Button>
        </>
      )}
      <label className="extension-checkbox">
        <input
          aria-label={`${unitId} compatibility reviewed`}
          type="checkbox"
          checked={investigation.service.compatibility_reviewed}
          onChange={(e) =>
            service({ compatibility_reviewed: e.target.checked }, true)
          }
        />
        I reviewed actual-service materials, sources and compatibility gaps.
      </label>
      <label className="extension-checkbox">
        <input
          aria-label={`${unitId} mechanical scope reviewed`}
          type="checkbox"
          checked={investigation.service.mechanical_scope_reviewed}
          onChange={(e) =>
            service({ mechanical_scope_reviewed: e.target.checked }, true)
          }
        />
        I reviewed mechanical requirements and excluded sizing/design scope.
      </label>
      <div className="extension-actions">
        <label>
          Baseline reviewer
          <input
            aria-label={`${unitId} baseline reviewer`}
            maxLength={150}
            value={reviewer}
            onChange={(e) => {
              setReviewer(e.target.value);
              setConfirmation(null);
            }}
          />
        </label>
      </div>
      <label className="extension-full-label">
        Review basis, limitations and exclusions
        <textarea
          aria-label={`${unitId} baseline basis`}
          maxLength={2000}
          value={basis}
          onChange={(e) => {
            setBasis(e.target.value);
            setConfirmation(null);
          }}
        />
      </label>
      <label className="extension-checkbox">
        <input
          aria-label={`${unitId} confirm baseline`}
          type="checkbox"
          checked={confirmation === signature}
          onChange={(e) => setConfirmation(e.target.checked ? signature : null)}
        />
        Apply this reviewed preliminary unit proposal to the BOM. It does not
        certify engineering suitability. Open challenges on the selected saved
        revision must be resolved.
      </label>
      <Button
        disabled={
          !!busy ||
          !report?.can_apply_baseline ||
          confirmation !== signature ||
          !reviewer.trim() ||
          !basis.trim()
        }
        onClick={apply}
      >
        {busy === "apply" ? "Applying…" : "Apply reviewed unit baseline"}
      </Button>
      <p role="status">{message}</p>
      {investigation.baseline_history.length > 0 && (
        <details>
          <summary>
            Baseline history · {investigation.baseline_history.length}
          </summary>
          {investigation.baseline_history.map((b, i) => (
            <p key={i}>
              {b.reviewed_at} · {b.reviewer} · {b.status} · {b.basis}
            </p>
          ))}
        </details>
      )}
    </div>
  );
}
