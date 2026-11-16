'use client';
import Link from 'next/link';
import {useId, useRef, useState} from 'react';
import {assessmentHref} from '../lib/assessment-navigation';
import {WorkspaceIcon} from './workspace-visuals';

export const pages=[['entry','Entry'],['overview','TEA overview'],['data','Engineering data'],['equipment','Equipment'],['capex','CAPEX'],['opex','OPEX'],['revenue','Revenue'],['cashflow','Cashflow'],['financial','Financial model'],['scenario','Scenario & Sensitivity Analysis'],['monte','Monte Carlo']] as const;
export const routes:Record<string,string>={entry:'/entry',overview:'/main-dashboard',data:'/data/equipment',equipment:'/capex/equipment',capex:'/capex',opex:'/opex',revenue:'/revenue',financial:'/financial-modelling',scenario:'/scenario-and-sensitivity',monte:'/monte-carlo/setup',cashflow:'/cashflow'};
const groups=[
 {label:'Workspace',keys:['entry','overview']},
 {label:'Engineering',keys:['data','equipment']},
 {label:'Economics',keys:['capex','opex','revenue']},
 {label:'Financial analysis',keys:['cashflow','financial','scenario','monte']},
] as const;

export function WorkspaceNavigation({page,id}:{page:string;id:string}){
 const [collapsed,setCollapsed]=useState(false);
 const [search,setSearch]=useState('');
 const navId=useId();
 const drawer=useRef<HTMLDialogElement>(null);
 const simple = ['equipment','capex','opex','revenue'].includes(page) ? page :
   ['cashflow','financial','scenario','monte-setup','monte-overview'].includes(page) ? 'financial' : 'entry';
 const links=(close?:()=>void)=><>
   {groups.filter(group=>group.keys.some(key=>pages.find(([candidate])=>candidate===key)?.[1].toLowerCase().includes(search.trim().toLowerCase()))).map(group=><div className="genesis-nav-group" key={group.label}>
    <p className="genesis-nav-group-label">{group.label}</p>
    {group.keys.map(key=>{
     const item=pages.find(([candidate])=>candidate===key);
     if(!item||!item[1].toLowerCase().includes(search.trim().toLowerCase()))return null;
     const label=item[1];
     return <div key={key}><Link onClick={close} aria-current={page===key?'page':undefined} href={assessmentHref(routes[key],id)}><WorkspaceIcon name={key}/><span>{label}</span>{page===key&&<i className="nav-dot"/>}</Link>{key==='monte'&&<div className="mc-nav-children"><Link onClick={close} aria-current={page==='monte-setup'?'page':undefined} href={assessmentHref('/monte-carlo/setup',id)}>Parameters & setup</Link><Link onClick={close} aria-current={page==='monte-overview'?'page':undefined} href={assessmentHref('/monte-carlo/overview',id)}>TEA overview</Link></div>}</div>;
    })}
   </div>)}
 </>;
 const simpleLink=(close?:()=>void)=><Link onClick={close} className="genesis-simple-link" href={assessmentHref(`/flow?stage=${simple}`,id)}>← Simple workspace</Link>;
 return <div className="genesis-navigation" data-collapsed={collapsed}>
  <div className="genesis-navigation-heading"><span>Navigation</span><button type="button" className="genesis-nav-collapse" aria-label={collapsed?'Expand workspace navigation':'Collapse workspace navigation'} aria-expanded={!collapsed} aria-controls={navId} onClick={()=>setCollapsed(value=>!value)}><span aria-hidden="true">{collapsed?'»':'«'}</span></button></div>
  {!collapsed&&<label className="genesis-nav-search"><span aria-hidden="true">⌕</span><input type="search" aria-label="Find a workspace" placeholder="Find workspace..." value={search} onChange={e=>setSearch(e.target.value)}/></label>}
  <nav id={navId} hidden={collapsed} className="genesis-nav-desktop" aria-label="Workspace navigation">{links()}</nav>
  {collapsed&&<nav className="genesis-nav-compact" aria-label="Compact workspace navigation">{pages.map(([key,label])=><Link key={key} href={assessmentHref(routes[key],id)} title={label} aria-label={label} aria-current={page===key?'page':undefined}><WorkspaceIcon name={key}/></Link>)}</nav>}
  <div className="genesis-simple-desktop" hidden={collapsed}>{simpleLink()}</div>
  <button className="genesis-nav-mobile" aria-label="Open workspace navigation" onClick={()=>drawer.current?.showModal()} type="button">Menu <span aria-hidden="true">☰</span></button>
  <dialog ref={drawer} className="genesis-nav-drawer" aria-label="Workspace navigation" onClick={event=>{if(event.target===event.currentTarget)drawer.current?.close();}}>
   <div className="genesis-nav-drawer-content">
    <div className="genesis-nav-drawer-head"><strong>Workspace navigation</strong><button type="button" aria-label="Close workspace navigation" onClick={()=>drawer.current?.close()}>×</button></div>
    <label className="genesis-nav-search"><span aria-hidden="true">⌕</span><input type="search" aria-label="Find a workspace" placeholder="Find workspace..." value={search} onChange={e=>setSearch(e.target.value)}/></label>
    <nav aria-label="Workspace destinations">{links(()=>drawer.current?.close())}</nav>
    {simpleLink(()=>drawer.current?.close())}
   </div>
  </dialog>
 </div>;
}
