/** Only URLs stored with source data are displayed. No author/book/DOI mappings. */
export type EvidenceTarget = {url:string;label:string;note:string;kind:'saved_url'};
export function evidenceTarget(source:unknown):EvidenceTarget|null {
 if(Array.isArray(source))return source.map(evidenceTarget).find(Boolean)||null;
 const row=source!==null&&typeof source==='object'?source as Record<string,unknown>:{};
 const exactPage=String(row.page_url||'');
 if(row.origin==='document' && /^\/api\/catalogue\/reference-documents\/[a-f0-9]{64}\/pages\/[1-9]\d*$/.test(exactPage))return {url:exactPage,label:'Open exact source page ↗',kind:'saved_url',note:'Original PDF page read from the configured OneDrive sync; no page number is inferred.'};
 const explicit=typeof source==='string'?source.trim():String(row.url||row.source_url||row.href||'').trim();
 if(!/^https?:\/\/\S+$/i.test(explicit))return null;
 try{const url=new URL(explicit);if(url.username||url.password)return null;
  const page=Number(row.pdf_page);if(/\.pdf$/i.test(url.pathname)&&Number.isInteger(page)&&page>0)url.hash=`page=${page}`;
  return {url:url.href,label:'Open source ↗',kind:'saved_url',note:'URL stored with this record. Retrieval alone does not independently verify a claim or page locator.'};
 }catch{return null;}
}
