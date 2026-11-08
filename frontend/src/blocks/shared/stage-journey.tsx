import Link from 'next/link';
import {assessmentHref} from '@/lib/assessment-navigation';
const steps=[['entry','Entry','/entry'],['data','Engineering data','/data/equipment'],['equipment','Equipment','/capex/equipment'],['capex','CAPEX','/capex'],['opex','OPEX','/opex'],['revenue','Revenue','/revenue'],['cashflow','Cashflow','/cashflow'],['financial','Financial model','/financial-modelling']];
export function StageJourney({page,id}:{page:string;id:string}){
 return <nav className="stage-journey" aria-label="Assessment workflow">{steps.map(([key,label,href],i)=><Link key={key} href={assessmentHref(href,id)} aria-current={page===key?'step':undefined}><span>{String(i+1).padStart(2,'0')}</span>{label}</Link>)}</nav>;
}
