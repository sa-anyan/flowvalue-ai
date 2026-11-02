'use client';
type Step={stage:string;status:string};
const labels:Record<string,string>={parse:'Parsing workbook',engineering_review:'Reviewing engineering data',engineering_advisor:'Selecting engineering assumptions',equipment:'Evaluating equipment',capex:'Calculating capital costs',opex:'Calculating operating costs',revenue:'Calculating revenue',financial:'Building financial model',financial_modelling:'Building financial model'};
const readable=(key:string)=>labels[key]||key.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
const failed=(s:string)=>/fail|error|unresolved|rejected/.test(s.toLowerCase());
const finished=(s:string)=>/complete|success|done|resolved|parsed|calculated|skipped|unavailable|fail|error/.test(s.toLowerCase());
export function AssessmentProgress({steps,running,error}:{steps:Step[];running:boolean;error?:string}){
 const current=steps.findLast(s=>!finished(s.status))||steps.at(-1);
 const complete=steps.filter(s=>finished(s.status)).length;
 const issues=Boolean(error)||steps.some(s=>failed(s.status)||/unavailable|skipped/.test(s.status.toLowerCase()));
 const progress=steps.length?Math.round(100*complete/steps.length):0;
 const done=!running&&steps.length>0;
 return <section className="fv-stage-progress" aria-label="Assessment processing status">
  <div className="fv-stage-head"><div><span className="fv-stage-eyebrow">ASSESSMENT ACTIVITY</span><h2 aria-live="polite">{running?(current?readable(current.stage):'Starting assessment…'):done?(issues?'Assessment completed with issues':'Assessment processing finished'):'Awaiting assessment'}</h2><p>{running?'FlowValue is processing your workbook. The indicator advances only when backend stages report completion.':done?'You can inspect the completed stages and any outstanding issues below.':'Upload a workbook to begin processing.'}</p></div><span className="fv-stage-state" data-state={running?'running':issues?'warning':'complete'}>{running?'● Processing':issues?'! Review issues':done?'✓ Finished':'Not started'}</span></div>
  <div className="fv-stage-track" role="progressbar" aria-label="Completed processing stages" aria-valuemin={0} aria-valuemax={steps.length||1} aria-valuenow={complete}><span style={{width:progress+'%'}}/></div>
  <div className="fv-stage-foot"><span>{running?'Working on: '+readable(current?.stage||'initialisation'):done?complete+' of '+steps.length+' stages reported complete':'No activity yet'}</span><span>{complete} / {steps.length} stages</span></div>
  <details className="fv-stage-history"><summary>View processing history <span>({steps.length} stages)</span></summary><ol>{steps.map((s,i)=><li key={i} data-state={failed(s.status)?'warning':finished(s.status)?'done':'active'}><span className="fv-history-symbol">{failed(s.status)?'!':finished(s.status)?'✓':'•'}</span><span><strong>{readable(s.stage)}</strong><small>{s.status.replaceAll('_',' ')}</small></span></li>)}</ol>{error&&<p role="alert" className="fv-stage-error">{error}</p>}</details>
 </section>;
}
