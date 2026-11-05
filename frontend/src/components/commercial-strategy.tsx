'use client';
import {useState} from 'react';
export function CommercialStrategy({description,busy,trace,onRun}:{description:string;busy:boolean;trace?:unknown;onRun:(description:string,researchConsent:boolean)=>void}){
 const [text,setText]=useState(description),[consent,setConsent]=useState(false);
 return <section><h2>Commercial Strategy Analyst</h2><p>Describe what earns income. The agent identifies separate payments, reviews tariff research and prepares assumptions for your approval before Python feeds them to finance. This creates a separate scenario and preserves the baseline.</p>
 <label className="field"><span>Revenue Box for the new scenario</span><textarea value={text} maxLength={12000} onChange={e=>setText(e.target.value)}/></label>
 <label className="check"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/>Allow external price research for missing tariffs. Selected process context is sent to OpenAI; usage charges apply. Results remain provisional assumptions.</label>
 <button disabled={busy||text.trim().length<10} onClick={()=>onRun(text,consent)}>Run Commercial Strategy Analyst →</button>
 {trace!==undefined&&<details><summary>Agent decisions, pricing basis and limitations</summary><pre>{JSON.stringify(trace,null,2)}</pre></details>}
 </section>;
}
