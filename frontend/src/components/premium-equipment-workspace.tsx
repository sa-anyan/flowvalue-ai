'use client';
import {ReactNode,useEffect,useMemo,useRef,useState} from 'react';

export type EquipmentCard = {key:string;tag:string;name:string;type:string;size:string;cost:string;status:string;model:string;rationale:string};
type Props={items:EquipmentCard[];selectedKey:string;onSelect:(key:string)=>void;dirty?:boolean;children?:ReactNode};
export function PremiumEquipmentWorkspace({items,selectedKey,onSelect,dirty=false,children}:Props){
 const [query,setQuery]=useState(''),[status,setStatus]=useState('all'),[sort,setSort]=useState('tag'),[layout,setLayout]=useState<'cards'|'list'>('cards'),[tab,setTab]=useState<'overview'|'cost'|'assumptions'>('overview'),[review,setReview]=useState(false),[page,setPage]=useState(0);
 const [drawerOpen,setDrawerOpen]=useState(false);
 const [expandedGroups,setExpandedGroups]=useState<string[]>([]);
 const triggerRef=useRef<HTMLButtonElement|null>(null);
 const closeRef=useRef<HTMLButtonElement|null>(null);
 const pageSize=30;
 useEffect(()=>{if(!drawerOpen)return;const previous=document.body.style.overflow;document.body.style.overflow='hidden';closeRef.current?.focus();return()=>{document.body.style.overflow=previous;};},[drawerOpen]);
 function closeDrawer(){if(dirty&&!window.confirm('You have unsaved equipment edits. Close the details without saving?'))return;setDrawerOpen(false);requestAnimationFrame(()=>triggerRef.current?.focus());}
 function handleKey(event:React.KeyboardEvent<HTMLDivElement>){if(event.key==='Escape'){event.stopPropagation();closeDrawer();}if(event.key==='Tab'){const nodes=Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href]')).filter(n=>n.getClientRects().length);if(!nodes.length)return;const first=nodes[0],last=nodes[nodes.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}}}
 const tone=(value:string)=>/unresolved|review|missing|excluded|failed|error|blocked/i.test(value)?'attention':/estimated|priced|calculated|complete|verified|success/i.test(value)?'ready':'neutral';
 const priced=(item:EquipmentCard)=>item.cost!=='Unpriced'&&item.cost!=='Unresolved'&&item.cost!=='';
 const formatStatus=(value:string)=>value.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
 const statuses=useMemo(()=>Array.from(new Set(items.map(x=>x.status).filter(Boolean))),[items]);
 const visible=useMemo(()=>items.filter(x=>(status==='all'||x.status===status)&&[x.tag,x.name,x.type,x.model].join(' ').toLowerCase().includes(query.trim().toLowerCase())).sort((a,b)=>sort==='name'?a.name.localeCompare(b.name):sort==='cost'?Number(b.cost.replace(/[^0-9.-]/g,''))-Number(a.cost.replace(/[^0-9.-]/g,'')):a.tag.localeCompare(b.tag)),[items,query,status,sort]);
 const nameKey=(name:string)=>name.trim().toLowerCase().replace(/\s+/g,' ');
 const pluralName=(name:string)=>{const words=name.trim().split(/\s+/);const last=words.pop()||'';const lower=last.toLowerCase();const irregular:Record<string,string>={machinery:'machinery',equipment:'equipment',series:'series',species:'species',manifold:'manifolds',vessel:'vessels'};const plural=irregular[lower]||(/(ss|us|is)$/.test(lower)?last+'es':/(ch|sh|x|z)$/.test(lower)?last+'es':/[^aeiou]y$/.test(lower)?last.slice(0,-1)+'ies':/s$/.test(lower)?last:last+'s');const result=last[0]===last[0]?.toUpperCase()?plural[0].toUpperCase()+plural.slice(1):plural;return [...words,result].join(' ');};

 const groups=useMemo(()=>{
  const buckets=new Map<string,EquipmentCard[]>();
  for(const item of visible){const key=nameKey(item.name);buckets.set(key,[...(buckets.get(key)||[]),item]);}
  const seen=new Set<string>();
  return visible.flatMap(item=>{const key=nameKey(item.name);if(seen.has(key))return [];seen.add(key);return [{key,members:buckets.get(key)!,name:item.name}];});
 },[visible]);
 const shownGroups=groups.slice(page*pageSize,(page+1)*pageSize);
 const getAmount=(cost:string)=>{const trimmed=cost.trim();if(!trimmed||/unpriced|unresolved|not provided/i.test(trimmed))return null;const numeric=trimmed.replace(/,/g,'');return /^[$£€]?\s*-?\d+(?:\.\d+)?$/.test(numeric)?Number(numeric.replace(/[$£€]/g,'')):null;};
 const costPrefix=(cost:string)=>(cost.match(/^[$£€]/)||[])[0]||'';
 function individual(item:EquipmentCard){return <button type="button" className="peq-card" data-tone={tone(item.status)} key={item.key} aria-pressed={drawerOpen&&current?.key===item.key} onClick={e=>{triggerRef.current=e.currentTarget;choose(item.key);}}><span className="peq-card-top"><span className="peq-tag">{item.tag}</span><span className="peq-status" data-tone={tone(item.status)}>{formatStatus(item.status)}</span></span><strong className="peq-name">{item.name}</strong><span className="peq-card-bottom"><span><small>Design size</small>{item.size}</span><span><small>Purchased cost</small><b>{item.cost}</b></span></span><span className="peq-card-open">Inspect →</span></button>}

 const current=visible.find(x=>x.key===selectedKey)||visible[0];
 const selectedIndex=visible.findIndex(x=>x.key===current?.key);
 const pricedCount=items.filter(priced).length;
 const unresolved=items.filter(x=>tone(x.status)==='attention'||!priced(x)).length;
 function choose(key:string){if(dirty&&drawerOpen&&key!==selectedKey&&!window.confirm('You have unsaved equipment edits. Switch equipment without saving?'))return;onSelect(key);setTab('overview');setDrawerOpen(true);}
 function step(direction:number){if(selectedIndex<0)return;const next=visible[selectedIndex+direction];if(next){if(dirty&&!window.confirm('You have unsaved equipment edits. Switch equipment without saving?'))return;onSelect(next.key);setTab('overview');setPage(Math.floor((selectedIndex+direction)/pageSize));}}
 return <section className="premium-equipment" aria-label="Equipment costing workspace">
  <div className="peq-head"><div><span className="eyebrow">EQUIPMENT REGISTER</span><h2>Equipment at a glance</h2><p>Choose an item to inspect its design, pricing and assumptions.</p></div><button className="secondary" type="button" aria-pressed={review} onClick={()=>{setReview(v=>!v);if(visible[0]){if(!drawerOpen)choose(current?.key||visible[0].key);else closeDrawer();}}}>{review?'Exit review':'Review equipment →'}</button></div>
  <div className="peq-stats"><div className="peq-stat-total"><small>Identified equipment</small><strong>{items.length}</strong></div><div className="peq-stat-priced"><small>With cost estimate</small><strong>{pricedCount}</strong></div><div className="peq-stat-review"><small>Needs attention</small><strong>{unresolved}</strong></div></div>
  <div className="peq-section-title"><div><h3>Equipment directory</h3><small>{visible.length} shown · Select a card for details</small></div><span className="peq-legend"><span className="peq-legend-ready">Estimated</span><span className="peq-legend-attention">Needs review</span></span></div>
  <div className="peq-controls"><label className="sr-only" htmlFor="peq-search">Search equipment</label><input id="peq-search" type="search" value={query} placeholder="Search tag, equipment or model…" onChange={e=>{setQuery(e.target.value);setPage(0);}}/><label className="sr-only" htmlFor="peq-status">Filter by status</label><select id="peq-status" value={status} onChange={e=>{setStatus(e.target.value);setPage(0);}}><option value="all">All statuses</option>{statuses.map(s=><option key={s} value={s}>{s.replaceAll('_',' ')}</option>)}</select><label className="sr-only" htmlFor="peq-sort">Sort equipment</label><select id="peq-sort" value={sort} onChange={e=>{setSort(e.target.value);setPage(0);}}><option value="tag">Sort by tag</option><option value="name">Sort by name</option><option value="cost">Sort by cost</option></select><button className="secondary" type="button" aria-label={layout==='cards'?'Switch to compact list':'Switch to cards'} onClick={()=>setLayout(v=>v==='cards'?'list':'cards')}>{layout==='cards'?'List view':'Card view'}</button></div>
  <div className={layout==='cards'?'peq-cards':'peq-list'} aria-label="Equipment selections">
    {shownGroups.map(group=>{
      if(group.members.length===1)return individual(group.members[0]);
      const open=expandedGroups.includes(group.key);
      const amounts=group.members.map(m=>getAmount(m.cost));
      const known=amounts.filter((v):v is number=>v!==null);
      const unavailable=group.members.length-known.length;
      const currencies=Array.from(new Set(group.members.filter((m,i)=>amounts[i]!==null).map(m=>costPrefix(m.cost))));
      const total=known.length&&currencies.length===1?currencies[0]+known.reduce((a,b)=>a+b,0).toLocaleString(undefined,{maximumFractionDigits:2}):'Unavailable';
      return <div className="peq-group" key={group.key}>
        <button type="button" className="peq-card peq-group-card" aria-expanded={open} aria-label={pluralName(group.name)+', '+group.members.length+' units'} onClick={()=>setExpandedGroups(g=>open?g.filter(v=>v!==group.key):[...g,group.key])}>
          <span className="peq-card-top"><span className="peq-tag">{group.members.length} UNITS</span><span className="peq-status">{unavailable?unavailable+' unpriced':'Grouped'}</span></span>
          <strong className="peq-name">{pluralName(group.name)}</strong>
          <span className="peq-card-bottom"><span><small>Total purchased cost</small><b>{total}</b></span><span className="peq-group-chevron" aria-hidden="true">{open?'⌃':'⌄'}</span></span>
          <span className="peq-card-open">{open?'Hide units ↑':'Show units ↓'}</span>
        </button>
        {open&&<div className="peq-group-items">{group.members.map(individual)}</div>}
      </div>;
    })}
    {!shownGroups.length&&<div className="peq-empty">No equipment matches these filters. <button type="button" onClick={()=>{setQuery('');setStatus('all');setPage(0);}}>Clear filters</button></div>}
  </div>
  {groups.length>pageSize&&<div className="peq-pager"><span>{page*pageSize+1}–{Math.min((page+1)*pageSize,groups.length)} of {groups.length} cards</span><button className="secondary" disabled={page===0} onClick={()=>setPage(v=>v-1)}>Previous</button><button className="secondary" disabled={(page+1)*pageSize>=groups.length} onClick={()=>setPage(v=>v+1)}>Next</button></div>}
  {drawerOpen&&current&&<div className="peq-drawer-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)closeDrawer();}}><div className="peq-drawer" role="dialog" aria-modal="true" aria-label={`${current.tag} equipment details`} onKeyDown={handleKey}><div className="peq-detail" id="equipment-details"><div className="peq-detail-head"><div><small>SELECTED EQUIPMENT · DETAILS</small><h3>{current.tag} · {current.name}</h3><span className="peq-status" data-tone={tone(current.status)}>{formatStatus(current.status)}</span></div><button type="button" className="peq-drawer-close" ref={closeRef} aria-label="Close equipment details" onClick={closeDrawer}>✕</button>{review&&<div className="peq-review-controls"><button className="secondary" disabled={selectedIndex<=0} onClick={()=>step(-1)}>← Previous</button><span>{selectedIndex+1} / {visible.length}</span><button className="secondary" disabled={selectedIndex<0||selectedIndex>=visible.length-1} onClick={()=>step(1)}>Next →</button></div>}</div>
   <div className="peq-tabs" role="tablist" aria-label="Equipment details">{([['overview','Overview'],['cost','Cost model'],['assumptions','Assumptions & edit']] as const).map(([id,label])=><button key={id} id={'peq-tab-'+id} role="tab" aria-selected={tab===id} aria-controls="peq-tabpanel" onClick={()=>setTab(id)}>{label}</button>)}</div>
   <div id="peq-tabpanel" role="tabpanel" aria-labelledby={'peq-tab-'+tab} className="peq-tab-content">
    {tab==='overview'&&<div className="peq-facts"><div><small>Equipment type</small><strong>{current.type}</strong></div><div><small>Design size</small><strong>{current.size}</strong></div><div><small>Selection status</small><strong>{current.status.replaceAll('_',' ')}</strong></div><div><small>Matched model</small><strong>{current.model}</strong></div></div>}
    {tab==='cost'&&<div className="peq-facts"><div><small>Purchased equipment cost</small><strong>{current.cost}</strong></div><div><small>Costing model</small><strong>{current.model}</strong></div><div className="peq-span"><small>Selection basis / engineering rationale</small><p>{current.rationale}</p></div><p className="peq-note peq-span">Only supported cost values and references are displayed; unresolved data is not estimated here.</p></div>}
    {tab==='assumptions'&&<div className="peq-edit"><div className="peq-edit-heading"><strong>Engineering assumptions</strong><span>Editable · Saved to current project</span></div>{children}<p className="peq-note">Save your changes, then use Run Again above to recalculate with Python.</p></div>}
   </div></div></div></div>}
 </section>;
}
