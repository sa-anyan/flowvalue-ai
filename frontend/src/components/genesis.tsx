import Link from 'next/link';
import type {ComponentPropsWithoutRef, ReactNode} from 'react';

export function GenesisPanel({className = '', ...props}: ComponentPropsWithoutRef<'section'>) {
  return <section className={`genesis-panel ${className}`} {...props} />;
}

export function GenesisKpi({label, value, exactValue, context, href, negative}: {
  label: string; value: string; exactValue?: string; context: string; href: string; negative?: boolean;
}) {
  return <Link className="genesis-kpi" href={href} data-signal={negative ? 'negative' : undefined}>
    <span className="genesis-kpi-label">{label}</span>
    <strong title={exactValue}>{value}</strong>
    <span className="genesis-kpi-context">{context}</span>
    <span className="genesis-kpi-arrow" aria-hidden="true">↗</span>
  </Link>;
}

export function GenesisControl({className = '', ...props}: ComponentPropsWithoutRef<'button'>) {
  return <button type="button" className={`genesis-control ${className}`} {...props} />;
}

export function GenesisChart({title, controls, children, className = ''}: {
  title: string; controls?: ReactNode; children: ReactNode; className?: string;
}) {
  return <article className={`genesis-panel genesis-chart ${className}`}>
    <div className="genesis-chart-header"><h3>{title}</h3>{controls}</div>
    {children}
  </article>;
}
