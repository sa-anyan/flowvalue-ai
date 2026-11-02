'use client';
type Step={stage:string;status:string};
const labels:Record<string,string>={parse:'Parsing workbook',engineering_review:'Reviewing engineering data',engineering_advisor:'Selecting engineering assumptions',equipment:'Evaluating equipment',capex:'Calculating capital costs',opex:'Calculating operating costs',revenue:'Calculating revenue',financial:'Building financial model',financial_modelling:'Building financial model'};
const readable=(key:string)=>labels[key]||key.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
const failed=(s:string)=>/fail|error|unresolved|rejected/.test(s.toLowerCase());
const finished=(s:string)=>/complete|success|done|resolved|parsed|calculated|skipped|unavailable|fail|error/.test(s.toLowerCase());
export function AssessmentProgress({steps,running,hasResults,error}:{steps:Step[];running:boolean;hasResults:boolean;error?:string}){
 const current=steps.findLast(s=>!finished(s.status))||steps.at(-1);
 const issues=Boolean(error)||steps.some(s=>failed(s.status)||/unavailable|skipped/.test(s.status.toLowerCase()));
 const done=!running&&hasResults;
 const halted=!running&&!hasResults&&Boolean(error);
 const progress=done?100:0;
 const recent=steps.at(-1);
 return <section className="fv-stage-progress" aria-label="Assessment processing status">
  <div className="fv-stage-head"><div><span className="fv-stage-eyebrow">ASSESSMENT ACTIVITY</span><h2 aria-live="polite">{running?(current?readable(current.stage):'Starting assessment…'):done?(issues?'Assessment completed with issues':'Assessment complete'):halted?'Assessment stopped — action required':'Awaiting assessment'}</h2><p>{running?'FlowValue is processing your workbook. The indicator advances only when backend stages report completion.':done?'Processing has finished. Review any outstanding engineering or financial issues below.':halted?'Processing stopped before results were available. View the history for the error.':'Upload a workbook to begin processing.'}</p></div><span className="fv-stage-state" data-state={running?'running':issues||halted?'warning':'complete'}>{running?'● Processing':done?(issues?'! Review issues':'✓ Finished'):halted?'! Stopped':'Not started'}</span></div>
  <div className="fv-stage-track" role="progressbar" aria-label="Assessment processing progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={running?undefined:progress} aria-valuetext={running?"Processing: "+readable(current?.stage||recent?.stage||"initialisation"):done?"Processing complete":halted?"Processing stopped":"Not started"}><span className={running?"fv-stage-indeterminate":""} style={{width:running?"35%":progress+"%"}}/></div>
  <div className="fv-stage-foot"><span>{running?'Working on: '+readable(current?.stage||recent?.stage||'initialisation'):done?'All processing finished':halted?'Stopped before results were ready':'No activity yet'}</span><span>{done?'100% complete':running?'Processing…':halted?'Stopped':'Not started'}</span></div>
  <details className="fv-stage-history"><summary>View processing history <span>({steps.length} stages)</span></summary><ol>{steps.map((s,i)=><li key={i} data-state={failed(s.status)?'warning':finished(s.status)?'done':'active'}><span className="fv-history-symbol">{failed(s.status)?'!':finished(s.status)?'✓':'•'}</span><span><strong>{readable(s.stage)}</strong><small>{s.status.replaceAll('_',' ')}</small></span></li>)}</ol>{error&&<p role="alert" className="fv-stage-error">{error}</p>}</details>
 </section>;
}
