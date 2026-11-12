'use client';
import { compact, num } from '@/lib/guided-flow';

/**
 * Minimal SVG charts for saved backend series. They only position values on
 * screen; scaling is the sole arithmetic and no figure is derived or totalled.
 */
export type Series = { label: string; values: (number | null)[]; tone: 'a' | 'b' | 'c' | 'neg' };

function scale(values: (number | null)[], height: number, pad = 18) {
  const finite = values.filter((v): v is number => v !== null);
  const lo = Math.min(0, ...finite),
    hi = Math.max(0, ...finite),
    span = hi - lo || 1;
  return { lo, hi, y: (v: number) => pad + (1 - (v - lo) / span) * (height - pad * 2) };
}

export function LineChart({ labels, series, height = 180, title }: { labels: string[]; series: Series[]; height?: number; title: string }) {
  const width = 600,
    left = 48,
    all = series.flatMap((s) => s.values),
    { lo, hi, y } = scale(all, height),
    x = (i: number) => left + (i / Math.max(1, labels.length - 1)) * (width - left - 10);
  if (!all.some((v) => v !== null)) return <p className="gf-muted">No saved values to chart yet.</p>;
  return (
    <figure className="gf-chart">
      <svg viewBox={`0 0 ${width} ${height + 18}`} role="img" aria-label={title}>
        <title>{title}</title>
        {[lo, (lo + hi) / 2, hi].map((v, i) => (
          <g key={i} className="gf-grid">
            <line x1={left} x2={width - 10} y1={y(v)} y2={y(v)} />
            <text x={0} y={y(v) + 4}>
              {compact(v)}
            </text>
          </g>
        ))}
        <line className="gf-zero" x1={left} x2={width - 10} y1={y(0)} y2={y(0)} />
        {series.map((s) => (
          <polyline
            key={s.label}
            className={`gf-series gf-tone-${s.tone}`}
            fill="none"
            points={s.values
              .map((v, i) => (v === null ? null : `${x(i)},${y(v)}`))
              .filter(Boolean)
              .join(' ')}
          />
        ))}
        {labels.map((l, i) =>
          i === 0 || i === labels.length - 1 || i % Math.max(1, Math.ceil(labels.length / 8)) === 0 ? (
            <text key={l + i} className="gf-axis" x={x(i)} y={height + 14} textAnchor="middle">
              {l}
            </text>
          ) : null,
        )}
      </svg>
      <figcaption className="gf-legend">
        {series.map((s) => (
          <span key={s.label}>
            <i className={`gf-tone-${s.tone}`} />
            {s.label}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}

export function BarChart({ labels, values, height = 180, title }: { labels: string[]; values: (number | null)[]; height?: number; title: string }) {
  const width = 600,
    left = 48,
    { lo, hi, y } = scale(values, height),
    slot = (width - left - 10) / Math.max(1, labels.length),
    bar = Math.max(2, Math.min(26, slot * 0.7));
  if (!values.some((v) => v !== null)) return <p className="gf-muted">No saved values to chart yet.</p>;
  return (
    <figure className="gf-chart">
      <svg viewBox={`0 0 ${width} ${height + 18}`} role="img" aria-label={title}>
        <title>{title}</title>
        {[lo, hi].map((v, i) => (
          <g key={i} className="gf-grid">
            <line x1={left} x2={width - 10} y1={y(v)} y2={y(v)} />
            <text x={0} y={y(v) + 4}>
              {compact(v)}
            </text>
          </g>
        ))}
        <line className="gf-zero" x1={left} x2={width - 10} y1={y(0)} y2={y(0)} />
        {values.map((v, i) =>
          v === null ? null : (
            <rect
              key={i}
              className={v < 0 ? 'gf-bar-neg' : 'gf-bar'}
              x={left + i * slot + (slot - bar) / 2}
              y={Math.min(y(v), y(0))}
              width={bar}
              height={Math.max(1, Math.abs(y(v) - y(0)))}
              rx="2"
            >
              <title>
                {labels[i]}: {compact(v)}
              </title>
            </rect>
          ),
        )}
        {labels.map((l, i) =>
          i === 0 || i === labels.length - 1 || i % Math.max(1, Math.ceil(labels.length / 8)) === 0 ? (
            <text key={l + i} className="gf-axis" x={left + i * slot + slot / 2} y={height + 14} textAnchor="middle">
              {l}
            </text>
          ) : null,
        )}
      </svg>
    </figure>
  );
}

/** Uncertainty fan: draws whichever percentile pairs the backend supplied (P5–P95, P10–P90, P25–P75) and the P50 line. */
export function FanChart({ rows, title, height = 200 }: { rows: Record<string, unknown>[]; title: string; height?: number }) {
  const pairs = [
    ['p5', 'p95', '90% band (P5–P95)', 'gf-band-90'],
    ['p10', 'p90', '80% band (P10–P90)', 'gf-band-80'],
    ['p25', 'p75', '50% band (P25–P75)', 'gf-band-50'],
  ] as const;
  const present = pairs.filter(([a, b]) => rows.some((r) => num(r[a]) !== null && num(r[b]) !== null));
  const width = 600,
    left = 48,
    all = rows.flatMap((r) => ['p5', 'p10', 'p25', 'p50', 'p75', 'p90', 'p95'].map((k) => num(r[k]))),
    { lo, hi, y } = scale(all, height),
    x = (i: number) => left + (i / Math.max(1, rows.length - 1)) * (width - left - 10);
  if (rows.length < 2 || !all.some((v) => v !== null)) return <p className="gf-muted">Run a Monte Carlo study to see uncertainty bands.</p>;
  const band = (a: string, b: string) => {
    const pts = rows.map((r, i) => [i, num(r[a]), num(r[b])] as const).filter(([, l, h]) => l !== null && h !== null);
    return [...pts.map(([i, l]) => `${x(i)},${y(l!)}`), ...pts.reverse().map(([i, , h]) => `${x(i)},${y(h!)}`)].join(' ');
  };
  return (
    <figure className="gf-chart">
      <svg viewBox={`0 0 ${width} ${height + 18}`} role="img" aria-label={title}>
        <title>{title}</title>
        {[lo, hi].map((v, i) => (
          <g key={i} className="gf-grid">
            <line x1={left} x2={width - 10} y1={y(v)} y2={y(v)} />
            <text x={0} y={y(v) + 4}>
              {compact(v)}
            </text>
          </g>
        ))}
        <line className="gf-zero" x1={left} x2={width - 10} y1={y(0)} y2={y(0)} />
        {present.map(([a, b, , cls]) => (
          <polygon key={a} className={cls} points={band(a, b)} />
        ))}
        <polyline
          className="gf-series gf-tone-a"
          fill="none"
          points={rows
            .map((r, i) => (num(r.p50) === null ? null : `${x(i)},${y(num(r.p50)!)}`))
            .filter(Boolean)
            .join(' ')}
        />
        {rows.map((r, i) =>
          i === 0 || i === rows.length - 1 || i % Math.max(1, Math.ceil(rows.length / 8)) === 0 ? (
            <text key={i} className="gf-axis" x={x(i)} y={height + 14} textAnchor="middle">
              Y{String(r.year)}
            </text>
          ) : null,
        )}
      </svg>
      <figcaption className="gf-legend">
        <span>
          <i className="gf-tone-a" />
          P50 median
        </span>
        {present.map(([a, , label, cls]) => (
          <span key={a}>
            <i className={cls} />
            {label}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
