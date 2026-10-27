"use client";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/client-api";
import { apiError } from "@/lib/assessment";
import type { UnitReport } from "@/lib/engineering";

type ReviewEvent = {
  id: string;
  unit_id: string;
  action: string;
  message: string;
  author_id: string;
  created_at: string;
  parent_id: string | null;
  input_digest: string;
};
type Snapshot = {
  version: { id: string; name: string; revision: number; user_id: string };
  is_owner: boolean;
  account_id: string;
  units: UnitReport[];
  events: ReviewEvent[];
  access: { id: string; reviewer_id: string; revoked_at: string | null }[];
  open_challenges: ReviewEvent[];
  notice: string;
};
export default function EngineeringReview() {
  const [versions, setVersions] = useState<
    { id: string; name: string; revision: number }[]
  >([]);
  const [identity, setIdentity] = useState("");
  const [selected, setSelected] = useState("");
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [unit, setUnit] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [grantFor, setGrantFor] = useState("");
  const [action, setAction] = useState("comment");
  const [message, setMessage] = useState("");
  const [parent, setParent] = useState("");
  useEffect(() => {
    const c = new AbortController();
    Promise.all([
      apiFetch("/api/engineering/reviews/identity", { signal: c.signal }),
      apiFetch("/api/projects", { signal: c.signal }),
    ])
      .then(async ([i, v]) => {
        if (!i.ok) throw Error(await apiError(i));
        if (!v.ok) throw Error(await apiError(v));
        setIdentity((await i.json()).account_id);
        setVersions(await v.json());
        const requested = new URL(window.location.href).searchParams.get(
          "version",
        );
        if (requested) setSelected(requested);
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => c.abort();
  }, []);
  useEffect(() => {
    if (!selected) return;
    const c = new AbortController();
    apiFetch(`/api/engineering/reviews/${selected}`, { signal: c.signal })
      .then(async (r) => {
        if (!r.ok) throw Error(await apiError(r));
        return r.json() as Promise<Snapshot>;
      })
      .then((s) => {
        setSnapshot(s);
        setUnit(s.units[0]?.unit_id || "");
        setError("");
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => c.abort();
  }, [selected]);
  const current = snapshot?.version.id === selected ? snapshot : null;
  const report = current?.units.find((r) => r.unit_id === unit);
  const grantSignature = `${selected}:${reviewer.trim()}`;
  async function refresh() {
    const r = await apiFetch(`/api/engineering/reviews/${selected}`);
    if (!r.ok) throw Error(await apiError(r));
    setSnapshot(await r.json());
  }
  async function mutate(path: string, body: unknown) {
    setBusy(true);
    setError("");
    try {
      const r = await apiFetch(`/api/engineering/reviews/${selected}/${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw Error(await apiError(r));
      await refresh();
      setMessage("");
      setGrantFor("");
      setParent("");
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Review request failed; retry.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="flow-page">
      <header className="flow-header">
        <div>
          <a href="/dashboard">← Return to dashboard / sign in</a>
          <h1>Saved-revision engineering review</h1>
          <p>
            Authenticated comments, agreements and challenges. Revision owners
            control access and resolve challenges. No institutional approval is
            implied.
          </p>
        </div>
      </header>
      <section className="panel extension-panel">
        <label>
          Your reviewer account ID
          <input aria-label="Reviewer account ID" readOnly value={identity} />
        </label>
        <p>
          Give this account ID to the owner if they wish to grant review access.
          This is not an API key. No enquiry or invitation email is sent.
        </p>
        <div className="extension-actions">
          <label>
            Saved revision
            <select
              aria-label="Saved engineering review revision"
              value={selected}
              onChange={(e) => {
                setSelected(e.target.value);
                setParent("");
                setGrantFor("");
              }}
            >
              <option value="">Choose an owned or shared revision</option>
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name} · v{v.revision}
                </option>
              ))}
            </select>
          </label>
          <Button
            variant="outline"
            disabled={!current || busy}
            onClick={() => refresh().catch((e) => setError(e.message))}
          >
            Refresh review
          </Button>
        </div>
        <p role="alert">{error}</p>
      </section>
      {current && (
        <>
          <section className="panel extension-panel">
            <h2>
              {current.version.name} · revision {current.version.revision}
            </h2>
            <p>
              {current.is_owner
                ? "You own this saved revision."
                : "Shared read-only revision. You may comment, challenge or record agreement; you cannot modify the owner’s saved model."}{" "}
              {current.notice}
            </p>
            <p>
              Open challenges: {current.open_challenges.length}. Baselines are
              applied from the working dashboard after owner review, not by a
              peer’s agreement.
            </p>
            {current.is_owner && (
              <details>
                <summary>Grant or revoke access to this revision</summary>
                <p>
                  Granting access exposes the entire saved revision, including
                  financials, streams, study evidence and engineering inputs, to
                  the named account until revoked. It does not grant later
                  revisions or model-editing rights. Previously downloaded data
                  cannot be recalled.
                </p>
                <div className="extension-actions">
                  <label>
                    Reviewer account UUID
                    <input
                      aria-label="Grant reviewer account UUID"
                      value={reviewer}
                      onChange={(e) => {
                        setReviewer(e.target.value);
                        setGrantFor("");
                      }}
                    />
                  </label>
                </div>
                <label className="extension-checkbox">
                  <input
                    aria-label="Confirm saved revision access grant"
                    type="checkbox"
                    checked={grantFor === grantSignature}
                    onChange={(e) =>
                      setGrantFor(e.target.checked ? grantSignature : "")
                    }
                  />
                  I authorize this exact account to read the entire selected
                  saved revision and participate in its review.
                </label>
                <Button
                  disabled={
                    busy ||
                    grantFor !== grantSignature ||
                    !/^[0-9a-f-]{36}$/i.test(reviewer.trim()) ||
                    reviewer.trim() === identity
                  }
                  onClick={() =>
                    mutate("access", {
                      reviewer_id: reviewer.trim(),
                      confirm_snapshot_access: true,
                    })
                  }
                >
                  Grant revision review access
                </Button>
                {current.access.map((a) => (
                  <p key={a.id}>
                    {a.reviewer_id} · {a.revoked_at ? "revoked" : "active"}{" "}
                    {!a.revoked_at && (
                      <Button
                        variant="outline"
                        disabled={busy}
                        onClick={() => mutate("revoke", { access_id: a.id })}
                      >
                        Revoke access for {a.reviewer_id}
                      </Button>
                    )}
                  </p>
                ))}
              </details>
            )}
          </section>
          <section className="panel extension-panel">
            <h2>Unit investigation & discussion</h2>
            <label>
              Unit
              <select
                aria-label="Peer review unit"
                value={unit}
                onChange={(e) => {
                  setUnit(e.target.value);
                  setParent("");
                }}
              >
                {current.units.map((u) => (
                  <option key={u.unit_id} value={u.unit_id}>
                    {u.unit_id} · {u.unit_kind}
                  </option>
                ))}
              </select>
            </label>
            {report && (
              <>
                <p>
                  {report.baseline_status.replaceAll("_", " ")} ·{" "}
                  {report.rule_version} · {report.blockers.length} unresolved
                  inputs
                </p>
                <p>
                  <strong>Service:</strong>{" "}
                  {report.case.service.duty_description || "not specified"}
                  <br />
                  <strong>Chemistry:</strong>{" "}
                  {report.case.service.fluid_composition || "not specified"}
                  <br />
                  <strong>Wetted / external:</strong>{" "}
                  {report.case.service.wetted_material} /{" "}
                  {report.case.service.shell_material}
                  <br />
                  <strong>Material reasoning:</strong>{" "}
                  {report.case.service.material_rationale || "not documented"}
                  <br />
                  <strong>Hypothesis:</strong>{" "}
                  {report.hypothesis || "not documented"}
                  <br />
                  <strong>Counter-evidence:</strong>{" "}
                  {report.counter_evidence || "not documented"}
                </p>
                <ul>
                  {report.blockers.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
                <details>
                  <summary>
                    Inspect full saved investigation, sizes and linked evidence
                  </summary>
                  <pre className="review-json">
                    {JSON.stringify(report, null, 2)}
                  </pre>
                </details>
              </>
            )}
            {current.events
              .filter((e) => e.unit_id === unit)
              .map((e) => (
                <article className="study-evidence" key={e.id}>
                  <strong>{e.action}</strong> · {e.author_id} · {e.created_at}
                  <p>{e.message}</p>
                  {e.parent_id && <p>Resolves challenge {e.parent_id}</p>}
                  {e.input_digest !== report?.digest && (
                    <p>Recorded against a different input fingerprint.</p>
                  )}
                </article>
              ))}
            <div className="extension-actions">
              <label>
                Review action
                <select
                  aria-label="Engineering review action"
                  value={action}
                  onChange={(e) => setAction(e.target.value)}
                >
                  <option value="comment">Comment</option>
                  <option value="challenge">
                    Challenge / request evidence
                  </option>
                  <option value="agree">
                    Record agreement (not certification)
                  </option>
                  {current.is_owner && (
                    <option value="resolve">
                      Resolve a challenge with an explanation
                    </option>
                  )}
                </select>
              </label>
              {action === "resolve" && current.is_owner && (
                <label>
                  Challenge
                  <select
                    aria-label="Challenge to resolve"
                    value={parent}
                    onChange={(e) => setParent(e.target.value)}
                  >
                    <option value="">Choose an open challenge</option>
                    {current.open_challenges
                      .filter((e) => e.unit_id === unit)
                      .map((e) => (
                        <option key={e.id} value={e.id}>
                          {e.message.slice(0, 100)}
                        </option>
                      ))}
                  </select>
                </label>
              )}
            </div>
            <label className="extension-full-label">
              Reasoning, challenge or resolution
              <textarea
                aria-label="Engineering review message"
                maxLength={3000}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
              />
            </label>
            <Button
              disabled={
                busy ||
                !report ||
                !message.trim() ||
                (action === "resolve" && (!current.is_owner || !parent))
              }
              onClick={() =>
                mutate("events", {
                  unit_id: unit,
                  action,
                  message,
                  parent_id: action === "resolve" ? parent : null,
                })
              }
            >
              Record engineering review event
            </Button>
            <p>
              Events are append-only and use the authenticated account identity.
              Refresh to see the latest review comments. Claimed technical
              competence and source applicability are not independently verified
              by this software.
            </p>
          </section>
        </>
      )}
    </main>
  );
}
