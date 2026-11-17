import {text,type Row} from '@/lib/guided-flow';
import {evidenceTarget} from '@/lib/evidence-source-links';

/** Claims cite the AI's saved retrieval evidence, never a frontend book mapping. */
export function AICitations({citations,basis}:{citations:Row[];basis?:unknown}) {
 const valid=citations.filter(c=>['retrieved','document_retrieved'].includes(text(c.status))&&evidenceTarget(c));
 return <div className="gf-ai-citations">
  {valid.length ? <div className="gf-ai-citation-links" aria-label="AI retrieved sources">{valid.map((c,i)=><a key={text(c.id)||i} href={evidenceTarget(c)!.url} target="_blank" rel="noopener noreferrer"
   title={[text(c.claim),text(c.locator),text(c.access_limitation),text(c.limitation),text(c.retrieved_at)].filter(Boolean).join(' · ')}><span>[{text(c.number)||i+1}]</span> {text(c.title)||'Source'}{c.pdf_page ? ` · PDF p. ${text(c.pdf_page)}` : ''} ↗</a>)}</div> : null}
  {valid.filter(c=>c.origin==='document').map((c,i)=><details className="gf-citation-excerpt" key={text(c.id)||i}><summary>Inspect quoted evidence · {text(c.locator)}</summary><blockquote>{text(c.supporting_quote)||'No matching quote supplied.'}</blockquote><small>{c.quote_match===true?'Quote matched the retrieved page text.':'Quote match failed; do not treat this as supported.'} Interpretation still requires review.</small>{/^https?:\/\//.test(text(c.url))&&<a href={text(c.url)} target="_blank" rel="noopener noreferrer">Original in OneDrive ↗</a>}<small>Use PDF page {text(c.pdf_page)} in OneDrive. Direct page jumping was not verified. Source SHA-256: {text(c.file_sha256)}</small></details>)}
  {valid.some(c=>c.support_level==='bibliographic_only') && <small>Bibliographic source only · underlying page/table was not verified.</small>}
  <small>{basis==='unsupported'?'Claim support is incomplete · source identity alone is not proof.':basis==='project_data'?'Based on supplied project data.':basis==='engineering_hypothesis'?'Engineering hypothesis · review required.':valid.length?'Links returned by AI retrieval · claims are not independently verified.':'No external source links were saved with this analysis.'}</small>
 </div>;
}
