"use client";

import { apiFetch } from "@/lib/client-api";

import { useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  BrainCircuit,
  ChevronRight,
  LoaderCircle,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import Markdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { apiError, AssessmentRequest, Stream, usd } from "@/lib/assessment";

export type AdvisorContext = {
  name: string;
  description: string;
  classification: string;
  region: string;
  raw_materials: { name: string; annual_cost: number }[];
  utilities: { name: string; annual_cost: number }[];
};
export const defaultContext: AdvisorContext = {
  name: "Untitled process",
  description: "",
  classification: "auto",
  region: "Not specified",
  raw_materials: [],
  utilities: [],
};
export type Suggestion = {
  id: string;
  title: string;
  parameter: string;
  suggested_change_pct: number;
  rationale: string;
  driver_share_pct: number;
  priority: string;
  scope: string;
  npv_change_usd: number | null;
};
type Profile = {
  project_name: string;
  classification: string;
  classification_basis: string;
  region: string;
  annualized_capital_cost: number;
  total_annualized_cost: number;
  lcop: number | null;
  category_shares_pct: Record<string, number>;
  top_drivers: {
    id: string;
    label: string;
    share_pct: number;
    annual_cost: number;
  }[];
  recommendations: Suggestion[];
  warnings: string[];
  research_themes: string[];
};
type Citation = {
  url: string;
  title: string;
  start_index: number;
  end_index: number;
};
type Briefing = {
  question: string;
  market_context_text: string;
  signature: string;
  text: string;
  citations: Citation[];
  running: boolean;
  error: string;
  status: string;
  evidence: string;
  retrieved_at?: string;
  model?: string;
};

function CitedText({
  text,
  citations,
}: {
  text: string;
  citations: Citation[];
}) {
  const parts: string[] = [];
  let cursor = 0;
  for (const c of [...citations].sort(
    (a, b) => a.start_index - b.start_index,
  )) {
    if (
      c.start_index < cursor ||
      c.end_index > text.length ||
      !/^https?:\/\//.test(c.url)
    )
      continue;
    parts.push(text.slice(cursor, c.start_index));
    const title = c.title.replaceAll("[", "(").replaceAll("]", ")");
    const url = encodeURI(c.url).replaceAll("(", "%28").replaceAll(")", "%29");
    parts.push(`[${title}](${url})`);
    cursor = c.end_index;
  }
  parts.push(text.slice(cursor));
  return (
    <div className="research-prose">
      <Markdown
        skipHtml
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {parts.join("")}
      </Markdown>
    </div>
  );
}

export function UniversalAdvisor({
  project,
  streams,
  ready,
  context,
  onContext,
  onApply,
  canApply,
  aiAvailable,
}: {
  aiAvailable: boolean;
  project: AssessmentRequest | null;
  streams: Stream[];
  ready: boolean;
  context: AdvisorContext;
  onContext: (v: AdvisorContext) => void;
  onApply: (r: Suggestion) => void;
  canApply: (r: Suggestion) => boolean;
}) {
  const signature = JSON.stringify(project ? { ...project, streams } : null);
  const [profile, setProfile] = useState<{
    signature: string;
    data: Profile;
  } | null>(null);
  const [failure, setFailure] = useState<{
    signature: string;
    message: string;
  } | null>(null);
  const [open, setOpen] = useState(false);
  const [brief, setBrief] = useState<Briefing | null>(null);
  const [question, setQuestion] = useState(
    "What macro risks could break this business case, and which parameters should we stress-test?",
  );
  const [marketText, setMarketText] = useState("");
  const scan = useRef<AbortController | null>(null);
  useEffect(() => {
    if (!project || !ready) return;
    const controller = new AbortController();
    const timer = setTimeout(
      () =>
        apiFetch("/api/assessment/universal-suggestions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: signature,
          signal: controller.signal,
        })
          .then(async (r) => {
            if (!r.ok) throw new Error(await apiError(r));
            return r.json();
          })
          .then((data: Profile) => {
            setProfile({ signature, data });
            setFailure(null);
          })
          .catch((e) => {
            if (e.name !== "AbortError")
              setFailure({ signature, message: e.message });
          }),
      200,
    );
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [signature, ready, project]);
  useEffect(() => () => scan.current?.abort(), [signature]);
  const current = profile?.signature === signature ? profile.data : null;
  const error = failure?.signature === signature ? failure.message : "";
  const active = !!brief?.running && brief.signature === signature;
  const stale =
    !!brief &&
    (brief.signature !== signature ||
      brief.question !== question ||
      brief.market_context_text !== marketText);
  async function runScan() {
    if (!current || !ready || !aiAvailable) return;
    scan.current?.abort();
    const controller = new AbortController();
    scan.current = controller;
    setOpen(true);
    setBrief({
      signature,
      question,
      market_context_text: marketText,
      text: "",
      citations: [],
      running: true,
      error: "",
      status: "Connecting to live research…",
      evidence: "pending",
    });
    try {
      let market_context = [];
      if (marketText.trim()) {
        const parsed = JSON.parse(marketText);
        if (!Array.isArray(parsed))
          throw new Error(
            "Market context must be a JSON array of title, summary, url and optional published_at objects.",
          );
        market_context = parsed;
      }
      const response = await apiFetch("/api/copilot/research-sensitivities", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project: JSON.parse(signature),
          question,
          market_context,
        }),
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(await apiError(response));
      if (!response.body)
        throw new Error("The browser did not receive a research stream.");
      const reader = response.body.getReader(),
        decoder = new TextDecoder();
      let buffer = "",
        completed = false;
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        buffer = buffer.replaceAll("\r\n", "\n");
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          const event = frame
            .split("\n")
            .find((x) => x.startsWith("event:"))
            ?.slice(6)
            .trim();
          const raw = frame
            .split("\n")
            .filter((x) => x.startsWith("data:"))
            .map((x) => x.slice(5).trim())
            .join("\n");
          if (!raw) continue;
          const item = JSON.parse(raw);
          if (event === "error") throw new Error(item.message);
          setBrief((prev) => {
            if (
              !prev ||
              prev.signature !== signature ||
              scan.current !== controller
            )
              return prev;
            if (event === "delta")
              return { ...prev, text: prev.text + item.text };
            if (event === "status") return { ...prev, status: item.message };
            if (event === "citation")
              return { ...prev, citations: [...prev.citations, item] };
            if (event === "complete")
              return {
                ...prev,
                text: item.text,
                citations: item.citations,
                running: false,
                evidence: item.evidence_status,
                retrieved_at: item.retrieved_at,
                model: item.model,
                error: item.warning ?? "",
                status: "Scan complete",
              };
            return prev;
          });
          if (event === "complete") completed = true;
        }
      }
      if (!completed)
        throw new Error(
          "The stream ended before completion. Partial text is not a finished market briefing.",
        );
    } catch (e) {
      if (!controller.signal.aborted)
        setBrief((prev) =>
          prev?.signature === signature && scan.current === controller
            ? {
                ...prev,
                running: false,
                error: e instanceof Error ? e.message : "Research failed",
                status: "Research unavailable",
              }
            : prev,
        );
    } finally {
      setBrief((prev) =>
        prev?.signature === signature && scan.current === controller
          ? { ...prev, running: false }
          : prev,
      );
    }
  }
  const shares = current?.category_shares_pct;
  return (
    <>
      <section
        className="panel universal-advisor"
        id="market-advisor"
        aria-label="AI Market & Risk Advisor"
      >
        <div className="panel-heading">
          <div>
            <div className="advisor-eyebrow">
              <BrainCircuit size={16} /> PROJECT INTELLIGENCE
            </div>
            <h2>AI Market & Risk Advisor</h2>
            <p>
              Calculated exposures first. Sourced market research when you need
              it.
            </p>
          </div>
          <Button
            className="primary-button"
            disabled={!current || !ready || active || !aiAvailable}
            onClick={runScan}
          >
            {active ? <LoaderCircle className="spin" /> : <Search />}Run Market
            Risk Scan
          </Button>
        </div>
        {!aiAvailable && (
          <p className="research-warning">
            Live research is unavailable until the AI connection is configured.
            Calculated recommendations below remain available.
          </p>
        )}
        <p className="advisor-entry-link">
          Project name, description, region and source costs are now edited in{" "}
          <a href="/entry#project-details">Entry</a>.
        </p>
        {error && (
          <p className="advisor-error" role="alert">
            {error}
          </p>
        )}
        {!current && !error && (
          <p className="advisor-loading">
            {ready ? (
              <>
                <LoaderCircle size={13} className="spin" />
                Profiling current cost structure…
              </>
            ) : (
              "Recommendations update after the assessment succeeds."
            )}
          </p>
        )}
        {current && (
          <>
            <div className="cost-profile-summary">
              <span className="quiet-badge">{current.classification}</span>
              <span>
                Annualized production cost{" "}
                <strong>{usd(current.total_annualized_cost)}/yr</strong>
              </span>
              <span>
                Capital <strong>{shares!.capex.toFixed(1)}%</strong>
              </span>
              <span>
                Fixed OPEX <strong>{shares!.fixed_opex.toFixed(1)}%</strong>
              </span>
              <span>
                Variable OPEX{" "}
                <strong>{shares!.variable_opex.toFixed(1)}%</strong>
              </span>
              <small>
                Within variable OPEX: materials{" "}
                {shares!.raw_materials.toFixed(1)}%, utilities{" "}
                {shares!.utilities.toFixed(1)}% of total.
              </small>
            </div>
            <div className="advisor-top-drivers">
              {current.top_drivers.map((d, i) => (
                <span key={d.id}>
                  {i + 1}. {d.label} <strong>{d.share_pct.toFixed(1)}%</strong>
                </span>
              ))}
            </div>
            <div className="recommendation-grid">
              {current.recommendations.map((r) => (
                <button
                  key={r.id}
                  className="recommendation-card"
                  disabled={!ready || !canApply(r)}
                  onClick={() => onApply(r)}
                  title={
                    !canApply(r)
                      ? "This compounded stress exceeds the ±50% slider limits. Adjust the scenario before applying."
                      : r.rationale
                  }
                >
                  <span className="recommendation-priority">
                    {r.priority} exposure
                    <ArrowUpRight size={14} />
                  </span>
                  <strong>{r.title}</strong>
                  <p>{r.rationale}</p>
                  <small>Scope: {r.scope}</small>
                  {r.npv_change_usd !== null && (
                    <span className="recommendation-impact">
                      Calculated ΔNPV <b>{usd(r.npv_change_usd, true)}</b>
                    </span>
                  )}
                  <span className="recommendation-action">
                    Apply {r.parameter.replaceAll("_", " ")}{" "}
                    {r.suggested_change_pct > 0 ? "+" : ""}
                    {r.suggested_change_pct}%<ChevronRight size={14} />
                  </span>
                </button>
              ))}
            </div>
            <details className="advisor-basis">
              <summary>Profile assumptions & sector themes</summary>
              <p>
                {current.classification_basis}. Sector themes are research
                topics, not current-market findings.
              </p>
              {current.research_themes.map((x) => (
                <p key={x}>{x}</p>
              ))}
              {current.warnings.map((x) => (
                <p key={x}>{x}</p>
              ))}
            </details>
          </>
        )}
        <div className="advisor-disclosure">
          <ShieldCheck size={14} />
          <span>
            Exposure rules run locally. Live scans send a summarized project
            cost profile to OpenAI and use web search. Suggested swings are
            stress scenarios, not probabilities.
          </span>
          {brief && (
            <button onClick={() => setOpen(true)}>
              Open briefing
              <ChevronRight size={12} />
            </button>
          )}
        </div>
      </section>
      {open && (
        <aside
          className="research-drawer"
          role="dialog"
          aria-label="Market risk research"
          aria-modal="false"
        >
          <div className="research-drawer-header">
            <div>
              <span className="advisor-eyebrow">
                <BrainCircuit size={16} /> ECONOMIST COPILOT
              </span>
              <h2>Market risk briefing</h2>
            </div>
            <button
              className="icon-button"
              aria-label="Close research sidebar"
              onClick={() => setOpen(false)}
            >
              <X size={19} />
            </button>
          </div>
          <div className="research-drawer-body">
            <p className="research-scope">
              {context.name} · {context.region}. No calibrated CAPEX-overrun
              probability is available.
            </p>
            <label className="research-question">
              Research question
              <textarea
                value={question}
                maxLength={1500}
                onChange={(e) => setQuestion(e.target.value)}
              />
            </label>
            <details className="advisor-basis">
              <summary>Add market context (optional)</summary>
              <p>
                Paste a JSON array with title, summary, url and optional
                published_at. User-supplied sources are marked unverified until
                researched.
              </p>
              <textarea
                aria-label="Market context JSON"
                value={marketText}
                onChange={(e) => setMarketText(e.target.value)}
                placeholder='[{"title":"Regional power outlook","summary":"…","url":"https://…","published_at":"2026-10-26"}]'
              />
            </details>
            <Button
              disabled={!current || !ready || active || !aiAvailable}
              onClick={runScan}
            >
              {active ? <LoaderCircle className="spin" /> : <Search />}
              {active ? "Researching…" : "Run Market Risk Scan"}
            </Button>
            {active && (
              <button
                className="text-button"
                onClick={() => {
                  scan.current?.abort();
                  setBrief((prev) =>
                    prev
                      ? {
                          ...prev,
                          running: false,
                          status: "Scan stopped",
                          error:
                            "Stopped before completion. Partial text is not a completed research result.",
                        }
                      : prev,
                  );
                }}
              >
                Stop scan
              </button>
            )}
            {stale && (
              <p className="research-warning">
                The scenario or research context changed. This briefing is out
                of date; run a new scan before using it.
              </p>
            )}
            {brief?.error && (
              <p role="alert" className="research-warning">
                {brief.error}
              </p>
            )}
            {brief && (
              <div className="research-status" role="status">
                {active && <LoaderCircle size={12} className="spin" />}
                {brief.status}
                {brief.retrieved_at && (
                  <small>
                    Retrieved {new Date(brief.retrieved_at).toLocaleString()} ·{" "}
                    {brief.model}
                  </small>
                )}
              </div>
            )}
            {brief?.text && (
              <CitedText text={brief.text} citations={brief.citations} />
            )}
            {brief && !brief.running && (
              <div className="research-evidence">
                {brief.evidence === "web_search_with_citations"
                  ? "AI draft from live search, with linked sources for review. Claims are not independently validated."
                  : "Live evidence not established."}
              </div>
            )}
            {!!brief?.citations.length && (
              <div className="research-evidence">
                <h3>Research sources</h3>
                <ul>
                  {Array.from(
                    new Map(brief.citations.map((c) => [c.url, c])).values(),
                  ).map((c) => (
                    <li key={c.url}>
                      <a href={c.url} target="_blank" rel="noreferrer">
                        {c.title || c.url}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {current && (
              <div className="research-tweaks">
                <h3>Calculated stress tests</h3>
                {current.recommendations.map((r) => (
                  <button
                    key={r.id}
                    disabled={!ready || !canApply(r) || stale}
                    onClick={() => onApply(r)}
                  >
                    {r.parameter.replaceAll("_", " ")}{" "}
                    {r.suggested_change_pct > 0 ? "+" : ""}
                    {r.suggested_change_pct}%<ArrowUpRight size={13} />
                  </button>
                ))}
              </div>
            )}
            <p className="research-footnote">
              No tax credit or carbon-price toggle is applied automatically.
              Policy eligibility requires current primary sources and
              project-specific review.
            </p>
          </div>
        </aside>
      )}
    </>
  );
}
