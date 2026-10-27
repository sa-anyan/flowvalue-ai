"use client";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/client-api";
import {
  apiError,
  type Incentive,
  type PolicyEvidence,
} from "@/lib/assessment";

const blank: PolicyEvidence = {
  profile: "custom",
  jurisdiction: "unknown",
  product: "unknown",
  construction_start: null,
  placed_in_service: null,
  emissions_kg_co2e_per_kg_h2: null,
  independent_verification: null,
  owner_trade_sale_use: null,
  no_conflicting_credit: null,
  electricity_and_emissions_rules_reviewed: null,
  wage_apprenticeship_reviewed: null,
  monetization_reviewed: null,
  reviewer: "",
  reviewed_on: null,
  source_urls: [],
  evidence_reference: "",
};
type Screen = {
  can_enable: boolean;
  status: string;
  rule_version: string;
  rules_reviewed_on: string;
  notice: string;
  sources: string[];
  checks: { key: string; label: string; status: string }[];
};
const questions = [
  [
    "independent_verification",
    "Independent production / emissions / sale-use verification",
  ],
  ["owner_trade_sale_use", "Ownership, trade/business and sale/use"],
  ["no_conflicting_credit", "No conflicting credits or elections"],
  [
    "electricity_and_emissions_rules_reviewed",
    "GREET/PER and applicable electricity sourcing rules",
  ],
  [
    "wage_apprenticeship_reviewed",
    "Wage/apprenticeship, exception and rate basis",
  ],
  ["monetization_reviewed", "Eligibility for selected monetization and timing"],
] as const;
export function PolicyReview({
  policy,
  onChange,
}: {
  policy: Incentive;
  onChange: (v: Partial<Incentive>) => void;
}) {
  const evidence = policy.evidence;
  const signature = evidence ? JSON.stringify(evidence) : "";
  const [sourceDraft, setSourceDraft] = useState<{
    signature: string;
    text: string;
  } | null>(null);
  const sourceSignature = JSON.stringify(evidence?.source_urls ?? []);
  const [response, setResponse] = useState<{
    signature: string;
    data?: Screen;
    error?: string;
  } | null>(null);
  useEffect(() => {
    if (!signature) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      apiFetch("/api/policy/screen", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: signature,
        signal: controller.signal,
      })
        .then(async (r) => {
          if (!r.ok) throw Error(await apiError(r));
          return r.json() as Promise<Screen>;
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
  }, [signature]);
  function edit(change: Partial<PolicyEvidence>) {
    onChange({
      evidence: { ...blank, ...evidence, ...change },
      enabled: false,
      eligibility_confirmed: false,
    });
  }
  const current = response?.signature === signature ? response : null;
  return (
    <div>
      <label className="extension-full-label">
        Policy review profile
        <select
          aria-label="Policy review profile"
          value={evidence?.profile ?? "manual"}
          onChange={(e) =>
            onChange({
              evidence:
                e.target.value === "manual"
                  ? null
                  : {
                      ...blank,
                      profile: e.target.value as PolicyEvidence["profile"],
                    },
              enabled: false,
              eligibility_confirmed: false,
            })
          }
        >
          <option value="manual">
            Manual custom scenario — no policy screening
          </option>
          <option value="custom">Custom policy — evidence checklist</option>
          <option value="us_45v">
            US 45V — preliminary eligibility screen
          </option>
        </select>
      </label>
      {!evidence ? (
        <p>
          Manual scenarios do not establish eligibility. Select a reviewed
          profile for structured evidence and rule checks.
        </p>
      ) : (
        <>
          <p>
            Changes disable the credit and reset confirmation. Rates remain
            user-entered; review inflation adjustments, tax treatment and
            timing. For 45V, operating year 1 begins at placed-in-service and
            the credit window ends after year 10. Passing this screen is not
            verified eligibility.
          </p>
          <div className="extension-actions">
            {evidence.profile === "us_45v" && (
              <>
                <label>
                  Production jurisdiction
                  <select
                    value={evidence.jurisdiction}
                    onChange={(e) =>
                      edit({
                        jurisdiction: e.target
                          .value as PolicyEvidence["jurisdiction"],
                      })
                    }
                  >
                    <option value="unknown">Unknown</option>
                    <option value="US">US / qualifying territory</option>
                    <option value="other">Other</option>
                  </select>
                </label>
                <label>
                  Product basis
                  <select
                    value={evidence.product}
                    onChange={(e) =>
                      edit({
                        product: e.target.value as PolicyEvidence["product"],
                      })
                    }
                  >
                    <option value="unknown">Unknown</option>
                    <option value="hydrogen_kg">kg hydrogen</option>
                    <option value="other">Other</option>
                  </select>
                </label>
                <label>
                  Construction start
                  <input
                    type="date"
                    value={evidence.construction_start ?? ""}
                    onBlur={(e) => {
                      const value = e.currentTarget.value || null;
                      if (value !== evidence.construction_start)
                        edit({ construction_start: value });
                    }}
                    onChange={(e) =>
                      edit({ construction_start: e.target.value || null })
                    }
                  />
                </label>
                <label>
                  Placed in service
                  <input
                    type="date"
                    value={evidence.placed_in_service ?? ""}
                    onBlur={(e) => {
                      const value = e.currentTarget.value || null;
                      if (value !== evidence.placed_in_service)
                        edit({ placed_in_service: value });
                    }}
                    onChange={(e) =>
                      edit({ placed_in_service: e.target.value || null })
                    }
                  />
                </label>
                <label>
                  Lifecycle kg CO2e/kg H2
                  <input
                    type="number"
                    min={0}
                    step="any"
                    value={evidence.emissions_kg_co2e_per_kg_h2 ?? ""}
                    onChange={(e) =>
                      edit({
                        emissions_kg_co2e_per_kg_h2:
                          e.target.value === "" ? null : Number(e.target.value),
                      })
                    }
                  />
                </label>
              </>
            )}
            {questions
              .filter(
                ([key]) =>
                  evidence.profile === "us_45v" ||
                  key === "monetization_reviewed",
              )
              .map(([key, label]) => (
                <label key={key}>
                  {label}
                  <select
                    value={
                      evidence[key] === null ? "unknown" : String(evidence[key])
                    }
                    onChange={(e) =>
                      edit({
                        [key]:
                          e.target.value === "unknown"
                            ? null
                            : e.target.value === "true",
                      })
                    }
                  >
                    <option value="unknown">Not reviewed</option>
                    <option value="true">Reviewed / satisfied</option>
                    <option value="false">Not satisfied</option>
                  </select>
                </label>
              ))}
            <label>
              Reviewer
              <input
                value={evidence.reviewer}
                maxLength={150}
                onChange={(e) => edit({ reviewer: e.target.value })}
              />
            </label>
            <label>
              Evidence review date
              <input
                type="date"
                value={evidence.reviewed_on ?? ""}
                onBlur={(e) => {
                  const value = e.currentTarget.value || null;
                  if (value !== evidence.reviewed_on)
                    edit({ reviewed_on: value });
                }}
                onChange={(e) => edit({ reviewed_on: e.target.value || null })}
              />
            </label>
          </div>
          <label className="extension-full-label">
            Supporting source URLs (one per line)
            <textarea
              value={
                sourceDraft?.signature === sourceSignature
                  ? sourceDraft.text
                  : evidence.source_urls.join("\n")
              }
              onChange={(e) => {
                const urls = e.target.value
                  .split("\n")
                  .map((v) => v.trim())
                  .filter(Boolean);
                setSourceDraft({
                  signature: JSON.stringify(urls),
                  text: e.target.value,
                });
                edit({ source_urls: urls });
              }}
            />
          </label>
          <label className="extension-full-label">
            Evidence / rate and eligibility reference
            <textarea
              value={evidence.evidence_reference}
              maxLength={1500}
              onChange={(e) => edit({ evidence_reference: e.target.value })}
            />
          </label>
          <div role="status">
            {current?.error ||
              (current?.data
                ? `Screen: ${current.data.status.replaceAll("_", " ")} · ${current.data.rule_version} · rules reviewed ${current.data.rules_reviewed_on}`
                : "Checking evidence…")}
          </div>
          {current?.data && (
            <>
              <ul>
                {current.data.checks.map((c) => (
                  <li key={c.key}>
                    {c.status.toUpperCase()}: {c.label}
                  </li>
                ))}
              </ul>
              <p>{current.data.notice}</p>
              {current.data.sources.map((url) => (
                <p key={url}>
                  <a href={url} target="_blank" rel="noreferrer">
                    Policy source ↗
                  </a>
                </p>
              ))}
            </>
          )}
          <label className="extension-checkbox">
            <input
              aria-label="Enable screened production credit"
              type="checkbox"
              checked={policy.enabled}
              disabled={
                !current?.data?.can_enable ||
                !policy.eligibility_confirmed ||
                !policy.basis.trim() ||
                (evidence.profile === "us_45v" &&
                  policy.start_year + policy.duration_years > 11)
              }
              onChange={(e) => onChange({ enabled: e.target.checked })}
            />
            Include reviewed scenario in cash flows and exports
          </label>
        </>
      )}
    </div>
  );
}
