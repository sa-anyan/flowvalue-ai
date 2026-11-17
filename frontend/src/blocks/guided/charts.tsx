'use client';
import { compact, num } from '@/lib/guided-flow';

/**
 * SVG charts for saved backend series. They only position values on screen;
 * scaling is the sole arithmetic and no figure is derived or totalled.
 *
 * Reading order is designed in: recessive grid, a firm zero line, values
 * labelled where the eye lands (bar tops, line ends), the extreme bar
 * highlighted, and a short draw-in animation that respects reduced motion.
 */
export type Series = { label: string; values: (number | null)[]; tone: 'a' | 'b' | 'c' | 'neg' };

/** Rounded axis ticks (1, 2, 2.5, 5 × 10^n) spanning the data and zero. */
export function niceTicks(values: (number | null)[], count = 4): number[] {
  const finite = values.filter((v): v is number => v !== null && Number.isFinite(v));
  const lo = Math.min(0, ...finite),
    hi = Math.max(0, ...finite);
  if (lo === hi) return [lo];
  const raw = (hi - lo) / count,
    power = 10 ** Math.floor(Math.log10(raw)),
    step = [1, 2, 2.5, 5, 10].map((m) => m * power).find((s) => s >= raw) ?? raw;
  const ticks: number[] = [];
  for (let t = Math.floor(lo / step) * step; t <= hi + step * 1e-9; t += step) ticks.push(Number(t.toPrecision(12)));
  if (ticks[ticks.length - 1] < hi) ticks.push(Number((ticks[ticks.length - 1] + step).toPrecision(12)));
  return ticks;
}

function scale(values: (number | null)[], height: number, pad = 18) {
  const ticks = niceTicks(values);
  const lo = ticks[0],
    hi = ticks[ticks.length - 1],
    span = hi - lo || 1;
  return { ticks, y: (v: number) => pad + (1 - (v - lo) / span) * (height - pad * 2) };
}

function Grid({ ticks, y, left, width }: { ticks: number[]; y: (v: number) => number; left: number; width: number }) {
  return (
    <>
      {ticks.map((v) => (
        <g key={v} className="gf-grid">
          <line x1={left} x2={width - 10} y1={y(v)} y2={y(v)} />
          <text x={left - 8} y={y(v) + 4} textAnchor="end">
            {compact(v)}
          </text>
        </g>
      ))}
      <line className="gf-zero" x1={left} x2={width - 10} y1={y(0)} y2={y(0)} />
    </>
  );
}

const xLabels = (n: number) => (i: number) => i === 0 || i === n - 1 || i % Math.max(1, Math.ceil(n / 8)) === 0;

export function LineChart({ labels, series, height = 180, title }: { labels: string[]; series: Series[]; height?: number; title: string }) {
  const width = 600,
    left = 52,
    right = 64,
    all = series.flatMap((s) => s.values),
    { ticks, y } = scale(all, height),
    x = (i: number) => left + (i / Math.max(1, labels.length - 1)) * (width - left - right);
  if (!all.some((v) => v !== null)) return <p className="gf-muted">No saved values to chart yet.</p>;
  const showX = xLabels(labels.length);
  // End labels: nudge apart so several series' last values never overlap.
  const ends = series
    .map((s, si) => {
      const i = s.values.map((v, k) => (v === null ? -1 : k)).filter((k) => k >= 0).pop();
      return i === undefined ? null : { si, y: y(s.values[i] as number) };
    })
    .filter(Boolean)
    .sort((a, b) => a!.y - b!.y) as { si: number; y: number }[];
  const endY: Record<number, number> = {};
  ends.forEach((e, k) => (endY[e.si] = k === 0 ? e.y : Math.max(e.y, endY[ends[k - 1].si] + 12)));
  return (
    <figure className="gf-chart">
      <svg viewBox={`0 0 ${width} ${height + 18}`} role="img" aria-label={title}>
        <title>{title}</title>
        <Grid ticks={ticks} y={y} left={left} width={width - right + 10} />
        {series.map((s, si) => {
          const pts = s.values.map((v, i) => (v === null ? null : ([x(i), y(v), v, i] as const))).filter(Boolean) as (readonly [number, number, number, number])[];
          const last = pts[pts.length - 1];
          return (
            <g key={s.label}>
              <polyline className={`gf-series gf-draw gf-tone-${s.tone}`} fill="none" pathLength={1} style={{ animationDelay: `${si * 120}ms` }} points={pts.map(([px, py]) => `${px},${py}`).join(' ')} />
              {pts.map(([px, py, v, i], k) => (
                <circle key={i} className={`gf-point gf-tone-${s.tone}`} cx={px} cy={py} r={k === pts.length - 1 ? 3.5 : 0}>
                  <title>{`${s.label} · ${labels[i] ?? ''}: ${compact(v)}`}</title>
                </circle>
              ))}
              {last && (
                <text className={`gf-end-label gf-tone-text-${s.tone}`} x={last[0] + 7} y={(endY[si] ?? last[1]) + 4}>
                  {compact(last[2])}
                </text>
              )}
            </g>
          );
        })}
        {labels.map((l, i) =>
          showX(i) ? (
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
    left = 52,
    { ticks, y } = scale(values, height),
    slot = (width - left - 10) / Math.max(1, labels.length),
    bar = Math.max(2, Math.min(26, slot * 0.7));
  if (!values.some((v) => v !== null)) return <p className="gf-muted">No saved values to chart yet.</p>;
  const finite = values.filter((v): v is number => v !== null);
  const peak = Math.max(...finite.map(Math.abs));
  // The highest and the lowest bar, labelled once each (first occurrence).
  const hiIndex = values.indexOf(Math.max(...finite)),
    loIndex = Math.min(...finite) < 0 ? values.indexOf(Math.min(...finite)) : -1;
  // Label every bar when there is room; otherwise only the extremes, so the eye goes there first.
  const labelAll = labels.length <= 12;
  const showX = xLabels(labels.length);
  return (
    <figure className="gf-chart">
      <svg viewBox={`0 0 ${width} ${height + 18}`} role="img" aria-label={title}>
        <title>{title}</title>
        <Grid ticks={ticks} y={y} left={left} width={width} />
        {values.map((v, i) => {
          if (v === null) return null;
          const top = Math.min(y(v), y(0)),
            h = Math.max(1, Math.abs(y(v) - y(0))),
            cx = left + i * slot + slot / 2,
            extreme = labelAll ? Math.abs(v) === peak : i === hiIndex || i === loIndex;
          return (
            <g key={i}>
              <rect
                className={`${v < 0 ? 'gf-bar-neg' : 'gf-bar'} gf-grow ${extreme ? 'gf-bar-peak' : ''}`}
                data-neg={v < 0}
                x={cx - bar / 2}
                y={top}
                width={bar}
                height={h}
                rx="2.5"
                style={{ animationDelay: `${Math.min(i, 30) * 18}ms` }}
              >
                <title>{`${labels[i]}: ${compact(v)}`}</title>
              </rect>
              {(labelAll || extreme) && (
                <text className={`gf-bar-label ${extreme ? 'gf-bar-label-peak' : ''}`} x={cx} y={v < 0 ? top + h + 12 : top - 5} textAnchor="middle">
                  {compact(v)}
                </text>
              )}
            </g>
          );
        })}
        {labels.map((l, i) =>
          showX(i) ? (
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
    left = 52,
    right = 92,
    all = rows.flatMap((r) => ['p5', 'p10', 'p25', 'p50', 'p75', 'p90', 'p95'].map((k) => num(r[k]))),
    { ticks, y } = scale(all, height),
    x = (i: number) => left + (i / Math.max(1, rows.length - 1)) * (width - left - right);
  if (rows.length < 2 || !all.some((v) => v !== null)) return <p className="gf-muted">Run a Monte Carlo study to see uncertainty bands.</p>;
  const band = (a: string, b: string) => {
    const pts = rows.map((r, i) => [i, num(r[a]), num(r[b])] as const).filter(([, l, h]) => l !== null && h !== null);
    return [...pts.map(([i, l]) => `${x(i)},${y(l!)}`), ...pts.reverse().map(([i, , h]) => `${x(i)},${y(h!)}`)].join(' ');
  };
  const end = rows[rows.length - 1],
    endX = x(rows.length - 1);
  // Label the last year's median and the widest band edges, where the spread is read.
  const outer = present[0];
  const endLabels = [
    ...(outer ? ([[outer[1], num(end[outer[1]])], [outer[0], num(end[outer[0]])]] as const) : []),
    ['p50', num(end.p50)] as const,
  ].filter(([, v]) => v !== null) as (readonly [string, number])[];
  const showX = xLabels(rows.length);
  return (
    <figure className="gf-chart">
      <svg viewBox={`0 0 ${width} ${height + 18}`} role="img" aria-label={title}>
        <title>{title}</title>
        <Grid ticks={ticks} y={y} left={left} width={width - right + 10} />
        {present.map(([a, b, , cls]) => (
          <polygon key={a} className={`${cls} gf-fade`} points={band(a, b)} />
        ))}
        <polyline
          className="gf-series gf-draw gf-tone-a"
          fill="none"
          pathLength={1}
          points={rows
            .map((r, i) => (num(r.p50) === null ? null : `${x(i)},${y(num(r.p50)!)}`))
            .filter(Boolean)
            .join(' ')}
        />
        {endLabels.map(([k, v]) => (
          <text key={k} className={`gf-end-label ${k === 'p50' ? 'gf-tone-text-a' : 'gf-end-label-muted'}`} x={endX + 7} y={y(v) + 4}>
            {k.toUpperCase()} {compact(v)}
          </text>
        ))}
        {rows.map((r, i) =>
          showX(i) ? (
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
