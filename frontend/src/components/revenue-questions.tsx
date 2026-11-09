'use client';
import {useEffect,useState} from 'react';
type Row=Record<string,unknown>;
const row=(v:unknown):Row=>v&&typeof v==='object'&&!Array.isArray(v)?v as Row:{};
const rows=(v:unknown):Row[]=>Array.isArray(v)?v.map(row):[];
export type RevenueClarification={question:string;answer:string};
export type AnswerPatch={group:'sales'|'commercial_lines';id:string;field:string;value:unknown;source:string};
export function applyAnswerPatches(config:unknown,patches:AnswerPatch[]){const next=structuredClone(row(config));for(const p of patches){if(!['sales','commercial_lines'].includes(p.group)||!['unit_price','rate','stream_key','saleable_fraction','sold_fraction','allocation_fraction','net_freight_deduction_per_unit','net_packaging_deduction_per_unit'].includes(p.field))throw Error('Unsupported answer field');const matches=rows(next[p.group]).filter(r=>r.id===p.id);if(matches.length!==1)throw Error('Answer must identify one existing revenue source');const line=matches[0];if(p.field==='stream_key'){if(typeof p.value!=='string'||!p.value.trim())throw Error('Choose an existing measured stream');}else{const n=Number(p.value);if(p.value===null||p.value===''||typeof p.value==='boolean'||!Number.isFinite(n)||n<0||p.field.endsWith('_fraction')&&n>1)throw Error('Use a valid non-negative value; fractions must be 0–1');}if(p.field==='rate')line.years=rows(line.years).map(y=>({...y,rate:p.value}));else line[p.field]=p.value;if(p.field==='unit_price')line.price_mode='assumed_price';line.rationale=String(line.rationale||'')+'; user-reviewed answer: '+p.source;}return next;}
export type QuestionCard={id:string;question:string;originals:string[];target?:Row;fx:boolean};
export function questionCards(questions:string[],config:unknown):QuestionCard[]{
 const c=row(config),targets=[...rows(c.sales),...rows(c.commercial_lines),...rows(c.pending_inputs)];
 const unique=questions.filter((q,i)=>questions.indexOf(q)===i&&!q.startsWith('Review and approve the current revenue'));
 const result:QuestionCard[]=[];
 for(const q of unique){const match=targets.filter(t=>String(t.name||'').length>3&&q.toLowerCase().includes(String(t.name).toLowerCase()));const target=match.length===1?match[0]:targets.length===1?targets[0]:undefined;
 const fx=/exchange.rate|\bconvert\b.*(?:GBP|USD|EUR)|(?:GBP|USD|EUR).*\bconvert\b/i.test(q);
 const prior=fx&&target?result.find(r=>r.fx&&r.target?.id===target.id):undefined;
 if(prior){prior.originals.push(q);continue;}result.push({id:String(result.length),question:q,originals:[q],target,fx});}
 return result;
}
export function statedPrice(text:string){
 const exp=/(?:(GBP|USD|EUR|£|\$|€)\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(GBP|USD|EUR|£|\$|€))\s*(?:\/|per\s+)(m[³3]|kg|tonne|t|litre|L|kWh)\b/gi;
 const matches=[...text.replaceAll("m³","m3").matchAll(exp)];if(matches.length!==1)return null;const m=matches[0],code=m[1]||m[4];return {amount:m[2]||m[3],currency:({'£':'GBP','$':'USD','€':'EUR'} as Record<string,string>)[code]||code.toUpperCase(),unit:m[5].replace('³','3')};
}
async function api(path:string,body?:unknown){const r=await fetch('/api/'+path,{cache:'no-store',...(body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{})});const v=await r.json();if(!r.ok)throw Error(v.detail||'Request failed');return v;}
type Answer = {text:string; choice?:string; patch?:AnswerPatch};
type Price = ReturnType<typeof statedPrice>;

function QuestionInput({active,config,report,researchDrafts,price,fx,fxLoading,busy,answer,onAnswer,onResearch}: {
 active:QuestionCard;config:unknown;report:unknown;researchDrafts:unknown;price:Price;fx:Row|null;fxLoading:boolean;
 busy:boolean;answer?:Answer;onAnswer:(answer:Answer)=>void;onResearch?:(target:string,focus:string)=>Promise<void>;
}){
 const [researching,setResearching]=useState(false),[error,setError]=useState('');
 const c=row(config),entities=rows(row(report).entities).filter(e=>e.kind==='material');
 const options:{id:string;label:string;answer:string;source?:string;url?:string;patch?:AnswerPatch}[]=[];
 if(active.fx&&fx)options.push({id:'fx',label:`Use ${Number(fx.amount).toLocaleString('en-GB',{maximumFractionDigits:6})} ${String(fx.currency)}/${price?.unit||'unit'}`,answer:`Use ${String(fx.amount)} ${String(fx.currency)}/${price?.unit||'unit'} converted from my stated ${price?.amount} ${price?.currency}/${price?.unit}. FX rate ${String(fx.rate)}, reference date ${String(fx.rate_date)}, source ${String(fx.source)}, ${String(fx.url)}. FX conversion only; do not claim this adjusts the price period. Retain the saved ${String(row(c.price_basis).price_period||'')} price-period scenario as a user assumption.`,source:`${String(fx.source)} · ${String(fx.rate_date)} · pinned informational rate, not live bank pricing; FX only, with the saved ${String(row(c.price_basis).price_period||'')} price-period scenario retained`,url:String(fx.url)});
 if(/stream|billable quantity|measured|mapping/i.test(active.question)&&!active.fx)for(const e of entities)options.push({id:'stream:'+String(e.key),label:String(e.identifier||e.key),answer:`For ${String(active.target?.name||'this revenue source')}, use the measured stream ${String(e.identifier)} (key ${String(e.key)}). Derive the billable quantity in Python from its documented units; do not invent missing measurements.`,source:'Existing engineering register; select only the relevant billing stream'});
 if(/hours|days.*operate|operating.*schedule/i.test(active.question)){const o=row(c.operating);if(o.days_per_year!=null&&o.hours_per_day!=null)options.push({id:'schedule',label:`Keep ${o.days_per_year} days/year, ${o.hours_per_day} hours/day`,answer:`Use the saved operating schedule: ${o.days_per_year} days/year and ${o.hours_per_day} hours/day, and preserve the saved annual production ramp.`,source:'Saved project assumptions'});}
 const canResearch=/\b(price|fee|rate|tariff)\b/i.test(active.question)&&!active.fx;
 const drafts=rows(researchDrafts).filter(d=>canResearch&&active.target&&d.target_id===active.target.id&&d.kind==='market');
 for(const d of drafts)for(const candidate of rows(d.candidates)){if(candidate.price==null||!candidate.source_url)continue;options.push({id:'research:'+String(candidate.source_url)+String(candidate.price),label:`${candidate.price} ${candidate.currency}/${candidate.quantity_unit} · ${candidate.name}`,answer:`For ${String(active.target?.name)}, use this provisional researched comparable for review: ${candidate.price} ${candidate.currency}/${candidate.quantity_unit}, period ${candidate.price_period}, source ${candidate.source_url}, source date ${candidate.source_date}, retrieved ${d.retrieved_at}. Applicability: ${candidate.applicability}. Scope: ${candidate.scope}. Uncertainty: ${candidate.uncertainty}. Do not treat it as a contract or quote; reconcile currency, units and period before calculation.`,source:`${candidate.source_date||'Date not reported'} · ${candidate.price_period} · ${candidate.uncertainty||'Unverified comparable'}`,url:String(candidate.source_url)});}
 const targetGroup=rows(c.sales).some(s=>s.id===active.target?.id)?'sales':rows(c.commercial_lines).some(s=>s.id===active.target?.id)?'commercial_lines':null;
 if(targetGroup==='sales'&&active.target){for(const [term,field,label] of [['saleable output','saleable_fraction','Assume all output meets the sale specification'],['sold output','sold_fraction','Assume all saleable output is sold'],['allocation','allocation_fraction','Allocate this stream to this product']]){if(active.question.includes(term))options.push({id:field,label,answer:`Use 1.0 for ${field} for ${String(active.target.name)} as an explicit analyst scenario, not a verified sale or specification.`,source:'User-selectable planning assumption; 100%, not researched market evidence',patch:{group:'sales',id:String(active.target.id),field,value:1,source:'Explicitly selected 100% scenario for '+field}});}}
 for(const option of options){if(!targetGroup||!active.target)continue;let field='';let value:unknown;
 if(option.patch)continue;
 if(option.id==='fx'){field=targetGroup==='sales'?'unit_price':'rate';value=fx?.amount;}
 else if(option.id.startsWith('stream:')){field='stream_key';value=option.id.slice(7);}
 if(field&&value!==undefined)option.patch={group:targetGroup,id:String(active.target.id),field,value,source:option.answer};}
 function typeAnswer(value:string){
  const question=active.question.toLowerCase();
  let field='';
  if(!active.fx&&/selling price|what fee|what.*rate/i.test(question))field=targetGroup==='sales'?'unit_price':'rate';
  if(targetGroup==='sales'){
   for(const [term,key] of [['saleable output','saleable_fraction'],['sold output','sold_fraction'],['allocation','allocation_fraction'],['freight deduction','net_freight_deduction_per_unit'],['packaging deduction','net_packaging_deduction_per_unit']]){
    if(question.includes(term))field=key;
   }
  }
  const n=Number(value);
  const patch:AnswerPatch|undefined=targetGroup&&active.target&&field&&value.trim()&&Number.isFinite(n)
   ?{group:targetGroup,id:String(active.target.id),field,value:n,source:'Explicit user answer: '+value}:undefined;
  onAnswer({text:value,patch});
 }
 async function research(){
  if(!active.target||!onResearch)return;
  setResearching(true);setError('');
  try{await onResearch(String(active.target.id),active.question.slice(0,300));}
  catch(e){setError((e as Error).message);}finally{setResearching(false);}
 }
 const selected=options.find(option=>option.id===answer?.choice);
 const title=active.fx?'How should we convert your stated price?':active.question;
 return <fieldset className="rv-basis-question" disabled={busy||researching}>
  <legend>{title}</legend>
  <input aria-label={title} value={answer?.text??''} maxLength={1200} onChange={e=>typeAnswer(e.target.value)} placeholder="Enter your answer"/>
  {active.fx&&fxLoading&&<small role="status">Looking up the reference exchange rate…</small>}
  {options.length>0&&<details className="rv-basis-options">
   <summary>{selected?'Suggested answer selected':'Use a suggested answer'}</summary>
   <select aria-label={'Suggested answer for '+title} value={selected?.id??''} onChange={e=>{
    const option=options.find(item=>item.id===e.target.value);
    if(option)onAnswer({text:option.answer,choice:option.id,patch:option.patch});
   }}>
    <option value="" disabled>Choose an option</option>
    {options.map(option=><option key={option.id} value={option.id}>{option.label}</option>)}
   </select>
   {selected&&<small>{selected.source}{selected.url&&<> · <a href={selected.url} target="_blank" rel="noreferrer">View source</a></>}</small>}
  </details>}
  {active.fx&&<details className="rv-basis-options"><summary>Original question</summary>{active.originals.map(q=><small key={q}>{q}</small>)}</details>}
  {active.target&&onResearch&&canResearch&&<details className="rv-basis-options"><summary>Research this answer</summary>
   <small>External search and AI usage charges apply.</small>
   <button type="button" className="secondary" disabled={busy||researching} onClick={()=>void research()}>{researching?'Researching…':'Search for options'}</button>
  </details>}
  {error&&<small role="alert">{error}</small>}
 </fieldset>;
}

export function RevenueQuestions({questions,config,text,report,researchDrafts,busy,onSubmit,onResearch,onApply,initialAnswers=[]}: {
 questions:string[];config:unknown;text:string;report:unknown;researchDrafts?:unknown;busy:boolean;
 onSubmit:(clarifications:RevenueClarification[])=>Promise<void>;
 onApply?:(patches:AnswerPatch[])=>Promise<void>;
 initialAnswers?:RevenueClarification[];
 onResearch?:(target:string,focus:string)=>Promise<void>;
}){
 const cards=questionCards(questions,config);
 const [answers,setAnswers]=useState<Record<string,Answer>>(()=>Object.fromEntries(cards.flatMap(card=>{
  const previous=initialAnswers.find(answer=>answer.question===card.originals.join('\n'));
  return previous?[[card.id,{text:previous.answer}]]:[];
 }))),[loading,setLoading]=useState(false),[error,setError]=useState('');
 const [fx,setFx]=useState<Row|null>(null),[fxLoading,setFxLoading]=useState(false),[fxError,setFxError]=useState(''),[retryFx,setRetryFx]=useState(0);
 const price=statedPrice(text),amount=price?.amount,sourceCurrency=price?.currency,currency=String(row(row(config).price_basis).currency||'');
 const needsFx=cards.some(card=>card.fx)&&Boolean(amount&&sourceCurrency&&currency&&sourceCurrency!==currency);
 useEffect(()=>{
  setFx(null);setFxError('');
  if(!needsFx){setFxLoading(false);return;}
  let current=true;
  setFxLoading(true);
  api('currency/convert',{amount,source_currency:sourceCurrency,target_currency:currency})
   .then(value=>{if(current)setFx(value);})
   .catch(e=>{if(current)setFxError(e.message);})
   .finally(()=>{if(current)setFxLoading(false);});
  return()=>{current=false;};
 },[needsFx,amount,sourceCurrency,currency,retryFx]);
 const answered=cards.filter(card=>answers[card.id]?.text.trim()).length;
 const direct=Boolean(onApply&&cards.every(card=>answers[card.id]?.patch));
 async function submit(){
  if(answered!==cards.length)return;
  setLoading(true);setError('');
  try{
   if(direct&&onApply){await onApply(cards.map(card=>answers[card.id].patch!));return;}
   await onSubmit(cards.map(card=>({question:card.originals.join('\n'),answer:answers[card.id].text.trim()})));
  }catch(e){setError((e as Error).message);}finally{setLoading(false);}
 }
 if(!cards.length)return null;
 return <section className="rv-basis-questions" aria-label="Revenue clarification">
  <h3>What’s missing</h3>
  <p>{cards.length-answered} {cards.length-answered===1?'answer':'answers'} needed</p>
  {cards.some(card=>initialAnswers.some(answer=>answer.question===card.originals.join('\n')))&&
   <p>Your previous answers are still here. The calculation needs more specific terms for the questions shown below.</p>}
  {cards.map(card=><QuestionInput key={card.id} active={card} config={config} report={report} researchDrafts={researchDrafts}
   price={price} fx={fx} fxLoading={fxLoading} busy={busy||loading} answer={answers[card.id]}
   onAnswer={answer=>setAnswers(previous=>({...previous,[card.id]:answer}))} onResearch={onResearch}/>)}
  {fxError&&<p role="alert">{fxError} <button type="button" className="secondary" disabled={busy||loading} onClick={()=>setRetryFx(n=>n+1)}>Retry exchange rate</button></p>}
  {error&&<p role="alert" className="error">{error}</p>}
  <button type="button" disabled={answered!==cards.length||busy||loading} onClick={()=>void submit()}>
   {loading?'Applying answers…':direct?'Apply answers & calculate':'Apply answers & review'}
  </button>
  {answered===cards.length&&!direct&&<small>Free-text terms will be interpreted before you confirm the calculation.</small>}
 </section>;
}
