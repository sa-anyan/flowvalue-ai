"use client";
import {
  object,
  array,
  number,
  full,
  type IncomeLine,
  type Row,
} from "./rate-lines";
export function PriceReview({
  line,
  expanded,
  proposal,
  researchNotice,
  busy,
  onChange,
  onResearch,
  onAccept,
}: {
  line: IncomeLine;
  expanded?: boolean;
  proposal?: Row;
  researchNotice?: string;
  busy: boolean;
  onChange: (change: Partial<IncomeLine>) => void;
  onResearch: () => void;
  onAccept: () => void;
}) {
  const review = object(line.price_review);
  function edit(key: string, value: unknown) {
    onChange({
      price_review: {
        ...review,
        origin: "user",
        rationale: String(
          review.rationale || "User-defined price scenario range",
        ),
        [key]: value,
        ...(["minimum", "maximum"].includes(key)
          ? {
              range_basis:
                "User-defined scenario bounds; references are retained for context, not proof of these bounds",
            }
          : {}),
      },
    });
  }
  return (
    <div className="rr-price-help">
      {line.price === null && (
        <div className="rr-find-price">
          <button
            className="secondary"
            disabled={busy || !line.name.trim()}
            onClick={onResearch}
          >
            Find a price for me
          </button>
          <small>
            Searches the web using AI credits. You choose whether to use the
            result.
          </small>
        </div>
      )}
      <details className="rr-price-review" open={expanded || Boolean(proposal)}>
        <summary>Price range & sources</summary>
        <div className="rr-range-grid">
          <label>
            Low price
            <input
              aria-label={`Low price ${line.name}`}
              type="number"
              min="0"
              step="any"
              placeholder="Unknown"
              value={number(review.minimum) ?? ""}
              disabled={busy}
              onChange={(e) => edit("minimum", number(e.target.value))}
            />
          </label>
          <label>
            Selected price
            <strong>
              {full(line.price)} / {line.price_unit}
            </strong>
          </label>
          <label>
            High price
            <input
              aria-label={`High price ${line.name}`}
              type="number"
              min="0"
              step="any"
              placeholder="Unknown"
              value={number(review.maximum) ?? ""}
              disabled={busy}
              onChange={(e) => edit("maximum", number(e.target.value))}
            />
          </label>
        </div>
        <label>
          Why this price?
          <textarea
            aria-label={`Price rationale ${line.name}`}
            value={String(review.rationale || "")}
            placeholder="Add a note about this price."
            disabled={busy}
            onChange={(e) => edit("rationale", e.target.value)}
          />
        </label>
        {array(review.sources).map((s, i) => (
          <p className="rr-citation" key={i}>
            {String(s.date || "Date not recorded")} ·{" "}
            {/^https?:\/\//.test(String(s.url)) ? (
              <a href={String(s.url)} target="_blank" rel="noreferrer">
                {String(s.title || s.url)}
              </a>
            ) : (
              String(s.title || "Reference")
            )}
          </p>
        ))}
        <p>
          {String(
            review.range_basis ||
              "User scenario bounds are assumptions, not verified market limits.",
          )}
        </p>
        <button
          className="secondary"
          disabled={busy || !line.name.trim()}
          onClick={onResearch}
        >
          Find another price ↗
        </button>
        <small>
          Searches the web using AI credits. Nothing changes until you accept.
        </small>
        {researchNotice && <p role="status">{researchNotice}</p>}
        {proposal && (
          <article className="rr-price-proposal">
            <strong>
              Suggested {full(proposal.selected)} {String(proposal.currency)}/
              {String(proposal.quantity_unit)}
            </strong>
            <p>
              Observed range {full(proposal.minimum)}–{full(proposal.maximum)} ·{" "}
              {String(proposal.price_period)}
            </p>
            <p>{String(proposal.rationale)}</p>
            <small>{String(proposal.range_basis)}</small>
            {array(proposal.sources).map((s, i) => (
              <p key={i}>
                <a href={String(s.url)} target="_blank" rel="noreferrer">
                  {String(s.title)}
                </a>{" "}
                · {String(s.date)}
              </p>
            ))}
            {Array.isArray(proposal.limitations) && (
              <p>{proposal.limitations.map(String).join(" · ")}</p>
            )}
            <button disabled={busy} onClick={onAccept}>
              Use this price
            </button>
          </article>
        )}
      </details>
    </div>
  );
}
