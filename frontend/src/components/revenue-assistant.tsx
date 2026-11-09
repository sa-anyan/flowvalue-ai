'use client';
import {useEffect,useRef,useState,type ReactNode} from 'react';
import './revenue-assistant.css';
import {RevenueQuestions,applyAnswerPatches,type RevenueClarification} from './revenue-questions';
import {assessmentHref} from '../lib/assessment-navigation';
type Row=Record<string,unknown>;
type AnnualProjection={lines:Row[];changes:{id:string;name:string;years:number[];missing:Record<string,string[]>}[];questions:string[]};
const annualTerms:Record<string,string>={rate:'Rate per billing unit',quantity:'Billable quantity',fixed_payment:'Annual fixed payment',
 minimum_quantity:'Minimum quantity',minimum_payment:'Annual minimum payment',availability:'Availability fraction',escalation:'Escalation fraction'};
const row=(v:unknown):Row=>v&&typeof v==='object'&&!Array.isArray(v)?v as Row:{};
const rows=(v:unknown):Row[]=>Array.isArray(v)?v.map(row):[];
export function revenueReview(config:unknown,questions:string[]){
 const c=row(config);
 return {lines:[...rows(c.sales).map(s=>({id:String(s.id),name:String(s.name||s.id),kind:'product',ratePeriod:'per_unit',unit:String(s.quantity_unit||''),source:String(s.stream_key||''),price:s.unit_price})),...rows(c.commercial_lines).map(s=>({id:String(s.id),name:String(s.name||s.id),kind:'commercial',ratePeriod:String(s.rate_period||''),unit:String(s.quantity_unit||''),source:String(s.stream_key||'Contract quantity'),price:rows(s.years)[0]?.rate}))],questions:[...new Set(questions.filter(q=>!q.startsWith('Review and approve the current revenue')))]};
}
export function RevenueAssistant({text,onText,config,questions,running,revision,report,onInterpret,onCalculate,revenueLines,ledger,researchDrafts,onResearch,assessmentId,interpretationError}:{assessmentId?:string;interpretationError?:string;text:string;onText:(v:string)=>void;config:unknown;questions:string[];running:boolean;revision:number;report:unknown;onInterpret:(clarifications?:RevenueClarification[])=>Promise<void>;researchDrafts?:unknown;onResearch?:(target:string,focus:string)=>Promise<void>;onCalculate:(config:Row)=>Promise<void>;revenueLines?:ReactNode;ledger?:ReactNode}){
 const dialog=useRef<HTMLDialogElement>(null);
 const checkedRevision=useRef<number|null>(null);
 const [panel,setPanel]=useState<'box'|'review'|'lines'|'ledger'>('box');
 const [draft,setDraft]=useState<Row>({}),[error,setError]=useState(''),[busy,setBusy]=useState(false),[awaiting,setAwaiting]=useState(false),[preflight,setPreflight]=useState<string[]|null>(null);
 const review=revenueReview(config,preflight??questions),local=revenueReview(draft,questions),currency=String(row(draft.price_basis).currency||'');
 const [checking,setChecking]=useState(false);
 const [projection,setProjection]=useState<AnnualProjection|null>(null);
 const [projectionChoice,setProjectionChoice]=useState<'review'|'apply'|'custom'|'custom-ready'>('review');
 const [lastAnswers,setLastAnswers]=useState<RevenueClarification[]>([]);
 const streams=rows(row(report).entities).filter(e=>e.kind==='material');
 useEffect(()=>{
  function show(event:Event){
   setPanel((event as CustomEvent<string>).detail==='lines'?'lines':'box');
   if(!dialog.current?.open)dialog.current?.showModal();
  }
  window.addEventListener('flowvalue:revenue-assistant',show);
  return()=>window.removeEventListener('flowvalue:revenue-assistant',show);
 },[]);
 async function openReview(){
  setPanel('review');
  checkedRevision.current=null;
  setDraft(structuredClone(row(config)));setError('');setPreflight(null);setProjection(null);setProjectionChoice('review');
  if(!assessmentId){checkedRevision.current=revision;return;}
  setChecking(true);
  try{
   const response=await fetch('/api/assessments/'+assessmentId+'/revenue-preflight',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision})});
   const value=await response.json();
   if(!response.ok)throw Error(value.detail||'Revenue review failed');
   checkedRevision.current=revision;
   setPreflight(value.questions);
   setProjection(value.annual_projection??null);
  }catch(e){setError((e as Error).message);}finally{setChecking(false);}
 }
 function close(){dialog.current?.close();}
 useEffect(()=>{if(awaiting&&!running&&!busy){setAwaiting(false);if(dialog.current?.open)void openReview();}},[awaiting,running,busy,revision]);
 function edit(group:string,index:number,key:string,value:unknown){setDraft(c=>({...c,[group]:rows(c[group]).map((r,i)=>i===index?{...r,[key]:value}:r)}));}
 const numeric=(v:string)=>v.trim()===''?null:Number(v);
 const missingTerms=projection?.changes.flatMap(line=>line.years.flatMap(year=>line.missing[String(year)].map(field=>({
  id:line.id,name:line.name,year,field,
  value:rows(rows(draft.commercial_lines).find(item=>item.id===line.id)?.years).find(item=>item.year===year)?.[field],
 }))))??[];
 function enterCustomTerms(){
  if(!projection)return;
  const lines=projection.lines.map(line=>{
   const change=projection.changes.find(item=>item.id===line.id);
   if(!change)return line;
   const original=rows(config&&row(config).commercial_lines).find(item=>item.id===line.id);
   return {...line,rationale:String(original?.rationale??'')+'; user supplied missing later-year forecast terms',
    years:rows(line.years).map(year=>({...year,...Object.fromEntries((change.missing[String(year.year)]??[]).map(field=>[field,null]))}))};
  });
  setDraft(current=>({...current,commercial_lines:lines}));
  setProjectionChoice('custom');
 }
 async function interpret(clarifications?:RevenueClarification[]){setError('');setBusy(true);try{await onInterpret(clarifications);setLastAnswers(clarifications??[]);setAwaiting(true);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 async function applyAndCalculate(patches:Parameters<typeof applyAnswerPatches>[1]){setBusy(true);setError('');try{const next=applyAnswerPatches(draft,patches);setDraft(next);await onCalculate(next);close();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 async function calculate(){setBusy(true);setError('');try{await onCalculate(draft);close();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 return <dialog id="revenue-assistant" ref={dialog} aria-labelledby="revenue-assistant-title"
  className="rv-assistant-dialog rv-assistant-popup" onClick={event=>{if(event.target===event.currentTarget)close();}}>
  <div className="rv-assistant-modal">
   <header className="rv-assistant-heading">
    <div><small>COMMERCIAL TOOLS</small><h2 id="revenue-assistant-title">Revenue Assistant</h2></div>
    <span className="rv-assistant-count">{running||awaiting?'Working…':review.lines.length?review.lines.length+' income sources':'Start with a description'}</span>
    <button type="button" className="secondary" aria-label="Close Revenue Assistant" onClick={close}>✕</button>
   </header>
   <div className="rv-assistant-menu" role="group" aria-label="Revenue Assistant menu">
    <button type="button" data-tone="box" aria-pressed={panel==='box'} onClick={()=>setPanel('box')}>
     <span className="rv-assistant-symbol" aria-hidden="true">✎</span><strong>Revenue Box</strong>
    </button>
    <button type="button" data-tone="interpret" disabled={running||busy||awaiting||!text.trim()}
     onClick={()=>{setPanel('box');void interpret();}}>
     <span className="rv-assistant-symbol" aria-hidden="true">✦</span><strong>Interpret with AI</strong>
    </button>
    <button type="button" data-tone="review" aria-pressed={panel==='review'} disabled={running||busy||checking||awaiting}
     onClick={()=>{if(checkedRevision.current===revision)setPanel('review');else void openReview();}}>
     <span className="rv-assistant-symbol" aria-hidden="true">✓</span><strong>Review &amp; calculate</strong>
    </button>
    <button type="button" data-tone="inputs" aria-pressed={panel==='lines'} onClick={()=>setPanel('lines')}>
     <span className="rv-assistant-symbol" aria-hidden="true">☷</span><strong>Revenue Lines</strong>
    </button>
    <button type="button" data-tone="ledger" aria-pressed={panel==='ledger'} onClick={()=>setPanel('ledger')}>
     <span className="rv-assistant-symbol" aria-hidden="true">▤</span><strong>Ledger</strong>
    </button>
   </div>
   <div className="rv-assistant-body">
    {error&&<p className="error" role="alert">{error}</p>}
    <section hidden={panel!=='box'} aria-labelledby="revenue-box-title">
     <h3 id="revenue-box-title">How does this project earn money?</h3>
     <label className="sr-only" htmlFor="revenue-message">Revenue description</label>
     <textarea id="revenue-message" value={text} maxLength={48000} disabled={running||busy||awaiting} onChange={event=>onText(event.target.value)}
      placeholder="Describe what you sell, who pays, and any prices or contract terms you know."/>
     <p className="rv-assistant-note">Known streams and saved operating assumptions are reused. AI interpretation incurs usage charges. No external price research starts automatically.</p>
     {awaiting&&<p role="status">Interpreting the Revenue Box…</p>}
    </section>
    <section hidden={panel!=='lines'} aria-label="Revenue Lines">{revenueLines}</section>
    <section hidden={panel!=='ledger'} className="rv-drawer-ledger" aria-label="Revenue Ledger">{ledger}</section>
    <section hidden={panel!=='review'} aria-labelledby="revenue-basis-title">
     <h3 id="revenue-basis-title">Confirm revenue basis</h3>
    {checking?<p role="status">Checking what’s needed…</p>:assessmentId&&preflight===null?
     <button type="button" className="secondary" onClick={()=>void openReview()}>Retry review check</button>:
     projection&&!projection.questions.length&&projectionChoice==='review'?
      <section className="rv-basis-questions">
       <h3>Set the later-year revenue terms</h3>
       <p>Year 1 terms are available. Use them to fill the missing later-year terms as a forecast. Measured volumes still follow each year's operating schedule.</p>
       <details className="rv-basis-optional"><summary>View affected income sources</summary><ul>
        {projection.changes.map(line=><li key={line.id}>{line.name} · operating {line.years.length===1?'year':'years'} {line.years.join(', ')}</li>)}
       </ul></details>
       <div className="rv-assistant-actions">
        <button type="button" disabled={busy||running} onClick={()=>{
         setDraft(current=>({...current,commercial_lines:projection.lines}));setPreflight(projection.questions);setProjectionChoice('apply');
        }}>Use Year 1 terms as a forecast</button>
        <button type="button" className="secondary" disabled={busy||running} onClick={enterCustomTerms}>Enter different terms</button>
       </div>
       {assessmentId&&<p><a href={assessmentHref('/cashflow',assessmentId)}>Edit the project horizon in Cash Flow</a></p>}
      </section>:
     projectionChoice==='custom'?
      <section className="rv-basis-questions">
       <h3>Enter the missing later-year terms</h3>
       <p>Only the blank terms are shown. Previously entered values stay in place.</p>
       {projection?.changes.flatMap(line=>line.years.map(year=><fieldset className="rv-basis-question" key={line.id+year}>
        <legend>{line.name} · operating year {year}</legend>
        <div className="rv-assistant-grid">{missingTerms.filter(term=>term.id===line.id&&term.year===year).map(term=><label key={term.field}>
         {annualTerms[term.field]}<input type="number" step="any" min={term.field==='escalation'?-.99:0} max={term.field==='availability'?1:undefined}
          value={String(term.value??'')} onChange={event=>{
           const value=numeric(event.target.value);
           setDraft(current=>({...current,commercial_lines:rows(current.commercial_lines).map(item=>item.id===term.id?
            {...item,years:rows(item.years).map(annual=>annual.year===term.year?{...annual,[term.field]:value}:annual)}:item)}));
          }}/>
        </label>)}</div>
       </fieldset>))}
       <div className="rv-assistant-actions">
        <button type="button" className="secondary" onClick={()=>setProjectionChoice('review')}>Back</button>
        <button type="button" disabled={missingTerms.some(term=>typeof term.value!=='number'||!Number.isFinite(term.value)||
         term.value<(term.field==='escalation'?-.99:0)||(term.field==='availability'&&term.value>1))}
         onClick={()=>{setPreflight([]);setProjectionChoice('custom-ready');}}>Review terms</button>
       </div>
      </section>:
     review.questions.length?
      <RevenueQuestions key={review.questions.join('|')} questions={review.questions} initialAnswers={lastAnswers} config={draft} text={text} report={report}
       researchDrafts={researchDrafts} busy={Boolean(running||busy)} onResearch={onResearch} onApply={applyAndCalculate} onSubmit={interpret}/>:
      local.lines.length?<div className="rv-basis-ready">
       <p>Review the assumptions below, then calculate.</p>
       {projectionChoice==='apply'&&<p role="status">Missing later-year terms use the Year 1 forecast. Existing terms are retained.</p>}
       {projectionChoice==='custom-ready'&&<p role="status">Your later-year terms are ready for calculation.</p>}
       <p className="rv-basis-context">{currency||'Currency missing'} · {String(row(draft.price_basis).price_period||'Price period missing')}<br/>
        {String(row(draft.operating).days_per_year??'—')} days/year · {String(row(draft.operating).hours_per_day??'—')} hours/day</p>
       <ul className="rv-basis-summary">{local.lines.map(line=><li key={line.kind+line.id}>
        <span><strong>{line.name}</strong><small>{String(streams.find(stream=>stream.key===line.source)?.identifier||line.source||'Stream to be confirmed')}</small></span>
        <span>{line.price==null?'Rate unavailable':new Intl.NumberFormat('en-GB',{maximumFractionDigits:6}).format(Number(line.price))+' '+currency+'/'+(line.ratePeriod==='annual'?'year':line.ratePeriod==='monthly'?'month':line.unit||'unit')}{line.kind==='commercial'&&<small>First-year rate</small>}</span>
       </li>)}</ul>
       <details className="rv-basis-optional"><summary>Edit assumptions</summary>
       <label className="field">Price period (YYYY or YYYY-MM)
        <input value={String(row(draft.price_basis).price_period??'')} placeholder="e.g. 2026-09"
         onChange={event=>setDraft(current=>({...current,price_basis:{...row(current.price_basis),price_period:event.target.value}}))}/>
       </label>
<div className="rv-assistant-grid">{[['days_per_year','Operating days / year',366],['hours_per_day','Operating hours / day',24]].map(([key,label,max])=><label key={key}>{label}<input type="number" min="0" max={Number(max)} value={String(row(draft.operating)[String(key)]??'')} onChange={e=>{setDraft({...draft,operating:{...row(draft.operating),[key]:numeric(e.target.value)}});}}/></label>)}</div>
 {rows(draft.sales).map((s,i)=><article key={String(s.id)}><h3>{String(s.name||s.id)}</h3><small>Product sales · {currency}/{String(s.quantity_unit||'unit')}</small><div className="rv-assistant-grid"><label>Net selling price / {String(s.quantity_unit||'unit')}<input type="number" min="0" step="any" value={String(s.unit_price??'')} onChange={e=>{edit('sales',i,'unit_price',numeric(e.target.value));setDraft(c=>({...c,sales:rows(c.sales).map((r,j)=>j===i?{...r,price_mode:'assumed_price'}:r)}));}}/></label><label>Saleable output fraction<input type="number" min="0" max="1" step="any" value={String(s.saleable_fraction??'')} onChange={e=>edit('sales',i,'saleable_fraction',numeric(e.target.value))}/></label><label>Fraction of saleable output sold<input type="number" min="0" max="1" step="any" value={String(s.sold_fraction??'')} onChange={e=>edit('sales',i,'sold_fraction',numeric(e.target.value))}/></label><label>Measured product stream<select value={String(s.stream_key||'')} onChange={e=>edit('sales',i,'stream_key',e.target.value)}><option value="">Choose existing stream</option>{streams.map(e=><option key={String(e.key)} value={String(e.key)}>{String(e.identifier||e.key)}</option>)}</select></label></div><small>0.8 means 80%. Production ramp is applied separately; editing sold fraction does not change the mass balance.</small></article>)}
 {rows(draft.commercial_lines).map((s,i)=><article key={String(s.id)}><h3>{String(s.name||s.id)}</h3><small>{String(s.category).replaceAll('_',' ')} · {String(s.quantity_unit)} · {String(s.rate_period)}</small><p>Saved first-year rate: {rows(s.years)[0]?.rate==null?'Missing':Number(rows(s.years)[0].rate).toLocaleString('en-GB',{maximumFractionDigits:6})} · fixed payment: {String(rows(s.years)[0]?.fixed_payment??'Missing')} {currency} · minimum payment: {String(rows(s.years)[0]?.minimum_payment??'Missing')} {currency}.</p><label>Set flat rate ({currency}/{String(s.quantity_unit)})<input type="number" min="0" step="any" placeholder="Leave existing annual rates unchanged" onChange={e=>{if(e.target.value.trim())edit('commercial_lines',i,'years',rows(s.years).map(y=>({...y,rate:numeric(e.target.value)})));}}/></label></article>)}
       </details>
      </div>:<p>Describe how the project earns money and choose Interpret with AI.</p>}
    {interpretationError&&!running&&<p className="error" role="alert">{interpretationError}</p>}
    </section>
   </div>
   {panel==='review'&&review.questions.length===0&&<footer>
    <button type="button" disabled={running||busy||checking||awaiting||!local.lines.length||Boolean(assessmentId&&preflight===null)}
     onClick={()=>void calculate()}>{busy?'Calculating…':'Confirm & calculate with Python'}</button>
   </footer>}
  </div>
 </dialog>;
}
