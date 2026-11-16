'use client';
import Link from 'next/link';
import {useId, useState} from 'react';
import {assessmentHref} from '../lib/assessment-navigation';
import {WorkspaceIcon} from './workspace-visuals';
export const pages=[['entry','Entry'],['overview','TEA overview'],['data','Engineering data'],['equipment','Equipment'],['capex','CAPEX'],['opex','OPEX'],['revenue','Revenue'],['cashflow','Cashflow'],['financial','Financial model'],['scenario','Scenario & Sensitivity Analysis'],['monte','Monte Carlo']] as const;
export const routes:Record<string,string>={entry:'/entry',overview:'/main-dashboard',data:'/data/equipment',equipment:'/capex/equipment',capex:'/capex',opex:'/opex',revenue:'/revenue',financial:'/financial-modelling',scenario:'/scenario-and-sensitivity',monte:'/monte-carlo/setup',cashflow:'/cashflow'};
export function WorkspaceNavigation({page,id}:{page:string;id:string}){
 const [collapsed,setCollapsed]=useState(false);
 const navId=useId();
 const simple = ['equipment','capex','opex','revenue'].includes(page) ? page :
   ['cashflow','financial','scenario','monte-setup','monte-overview'].includes(page) ? 'financial' : 'entry';
 return <div className="genesis-navigation" data-collapsed={collapsed}>
  <div className="genesis-navigation-heading"><span>WORKSPACES</span><button type="button" className="genesis-nav-collapse" aria-label={collapsed?'Expand workspace navigation':'Collapse workspace navigation'} aria-expanded={!collapsed} aria-controls={navId} onClick={()=>setCollapsed(value=>!value)}>{collapsed?'▾':'▴'}</button></div>
  <Link className="genesis-simple-link" href={assessmentHref(`/flow?stage=${simple}`, id)}>← Simple workspace</Link>
  <nav id={navId} hidden={collapsed} aria-label="Workspace navigation">{pages.map(([key,label])=><div key={key}><Link aria-current={page===key?'page':undefined} href={assessmentHref(routes[key],id)}><WorkspaceIcon name={key}/><span>{label}</span>{page===key&&<i className="nav-dot"/>}</Link>{key==='monte'&&<div className="mc-nav-children"><Link aria-current={page==='monte-setup'?'page':undefined} href={assessmentHref('/monte-carlo/setup',id)}>Parameters & setup</Link><Link aria-current={page==='monte-overview'?'page':undefined} href={assessmentHref('/monte-carlo/overview',id)}>TEA overview</Link></div>}</div>)}</nav>
 </div>;
}
