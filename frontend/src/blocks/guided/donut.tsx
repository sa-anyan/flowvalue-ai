'use client';
import { useState } from 'react';
import { compact } from '@/lib/guided-flow';

/** Fixed, colour-blind-aware order; colour follows the item, never its rank. */
export const DONUT_COLORS = ['#2a78d6', '#1baf7a', '#eda100', '#e87ba4', '#6250d6', '#eb6834', '#008300', '#49718f'];

export type DonutItem = { label: string; value: number; color?: string };

/** Share of total as a readable percent: 1 decimal under 10 %, whole numbers above. */
export function sharePercent(value: number, total: number): string {
  if (!(total > 0)) return '—';
  const pct = (value / total) * 100;
  return pct > 0 && pct < 0.1 ? '<0.1%' : `${pct < 10 ? pct.toFixed(1) : Math.round(pct)}%`;
}

/** Positive items, largest first, with their colour and share. Python's values are only positioned, never changed. */
export function donutSlices(items: DonutItem[]) {
  const shown = items.map((item, i) => ({ ...item, color: item.color || DONUT_COLORS[i % DONUT_COLORS.length] })).filter((item) => Number.isFinite(item.value) && item.value > 0);
  const total = shown.reduce((sum, item) => sum + item.value, 0);
  let start = 0;
  return {
    total,
    slices: shown
      .sort((a, b) => b.value - a.value)
      .map((item) => {
        const fraction = total ? item.value / total : 0;
        const slice = { ...item, fraction, start, share: sharePercent(item.value, total) };
        start += fraction;
        return slice;
      }),
  };
}

/**
 * Animated donut with the total in the centre and a legend of value and share.
 * Slices sweep in once; hovering or focusing a legend row highlights its slice.
 */
export function Donut({ items, title, centerLabel = 'Total', currency, size = 168 }: { items: DonutItem[]; title: string; centerLabel?: string; currency?: string; size?: number }) {
  const [active, setActive] = useState<string | null>(null);
  const { total, slices } = donutSlices(items);
  if (!slices.length) return null;
  const r = 60,
    c = 2 * Math.PI * r,
    gap = slices.length > 1 ? 1.5 : 0;
  return (
    <figure className="gf-donut" aria-label={title}>
      <svg viewBox="0 0 160 160" width={size} height={size} role="img" aria-label={`${title}: ${slices.map((s) => `${s.label} ${compact(s.value)} (${s.share})`).join(', ')}`}>
        <g transform="rotate(-90 80 80)">
          <circle cx="80" cy="80" r={r} className="gf-donut-track" />
          {slices.map((s, i) => {
            const length = Math.max(0, s.fraction * c - gap);
            return (
              <circle
                key={s.label + i}
                cx="80"
                cy="80"
                r={r}
                className="gf-donut-slice"
                data-dim={active !== null && active !== s.label}
                stroke={s.color}
                // Inline style (not attributes) so the sweep animation ends at this slice's length.
                style={{ strokeDasharray: `${length} ${c - length}`, strokeDashoffset: -s.start * c, animationDelay: `${i * 70}ms` }}
                onMouseEnter={() => setActive(s.label)}
                onMouseLeave={() => setActive(null)}
              >
                <title>{`${s.label}: ${compact(s.value)} ${currency ?? ''} (${s.share})`}</title>
              </circle>
            );
          })}
        </g>
        {slices.map((s) => {
          if (s.fraction < 0.08) return null; // small slices are read from the legend
          const angle = (s.start + s.fraction / 2) * 2 * Math.PI - Math.PI / 2;
          return (
            <text key={'l' + s.label} className="gf-donut-pct" x={80 + r * Math.cos(angle)} y={80 + r * Math.sin(angle) + 3.5} textAnchor="middle">
              {s.share}
            </text>
          );
        })}
        <text className="gf-donut-total" x="80" y="80" textAnchor="middle">
          {compact(active ? slices.find((s) => s.label === active)?.value : total)}
        </text>
        <text className="gf-donut-caption" x="80" y="97" textAnchor="middle">
          {active ? slices.find((s) => s.label === active)?.share : `${centerLabel}${currency ? ` · ${currency}` : ''}`}
        </text>
      </svg>
      <figcaption>
        <ul className="gf-donut-legend">
          {slices.map((s) => (
            <li key={s.label} data-dim={active !== null && active !== s.label} tabIndex={0} onMouseEnter={() => setActive(s.label)} onMouseLeave={() => setActive(null)} onFocus={() => setActive(s.label)} onBlur={() => setActive(null)}>
              <i style={{ background: s.color }} aria-hidden="true" />
              <span>{s.label}</span>
              <strong>{compact(s.value)}</strong>
              <em>{s.share}</em>
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  );
}
