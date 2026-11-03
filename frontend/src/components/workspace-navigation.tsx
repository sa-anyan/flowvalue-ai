'use client';
import Link from 'next/link';
import {assessmentHref} from '../lib/assessment-navigation';
import {WorkspaceIcon} from './workspace-visuals';
export const pages=[['entry','Entry'],['overview','TEA overview'],['data','Engineering data'],['equipment','Equipment'],['capex','CAPEX'],['opex','OPEX'],['revenue','Revenue'],['financial','Financial model'],['monte','Monte Carlo']] as const;
export const routes:Record<string,string>={entry:'/entry',overview:'/main-dashboard',data:'/data/equipment',equipment:'/capex/equipment',capex:'/capex',opex:'/opex',revenue:'/revenue',financial:'/financial-modelling',monte:'/monte-carlo/setup'};
export function WorkspaceNavigation({page,id}:{page:string;id:string}){return <nav>{pages.map(([key,label])=><div key={key}><Link aria-current={page===key?'page':undefined} href={assessmentHref(routes[key],id)}><WorkspaceIcon name={key}/><span>{label}</span>{page===key&&<i className="nav-dot"/>}</Link>{key==='monte'&&<div className="mc-nav-children"><Link aria-current={page==='monte-setup'?'page':undefined} href={assessmentHref('/monte-carlo/setup',id)}>Parameters & setup</Link><Link aria-current={page==='monte-overview'?'page':undefined} href={assessmentHref('/monte-carlo/overview',id)}>TEA overview</Link></div>}</div>)}</nav>;}
