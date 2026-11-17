"""Claim-level AI citations; URL provenance comes from provider tools, never the model."""
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit


def safe_url(value):
    if not isinstance(value, str) or len(value) > 4096 or any(c.isspace() for c in value):
        return None
    try:
        p = urlsplit(value)
        if p.scheme not in {'http', 'https'} or not p.hostname or p.username or p.password:
            return None
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or '/', p.query, ''))
    except ValueError:
        return None


def retrieved_sources(raw):
    """Only provider web-search outputs and citation annotations establish URL provenance."""
    sources = {}
    observed = datetime.now(timezone.utc).isoformat()
    for item in raw.get('output', []):
        candidates = []
        if item.get('type') == 'web_search_call':
            candidates += item.get('action', {}).get('sources', [])
        if item.get('type') == 'message':
            for part in item.get('content', []):
                candidates += [a for a in part.get('annotations', []) if a.get('type') == 'url_citation']
        for candidate in candidates:
            url = safe_url(candidate.get('url'))
            if url:
                sources[url] = {'url': url, 'title': str(candidate.get('title') or '')[:300], 'retrieved_at': observed}
    return list(sources.values())[:64]


def validate_citations(response, document_pages=(), document_links=None):
    import re
    import unicodedata
    def normal(value):return re.sub(r"\s+", " ", unicodedata.normalize('NFKC', str(value))).strip().casefold()
    retrieved = {r['url']: r for r in response.pop('_retrieved_sources', []) if safe_url(r.get('url'))}
    documents = {r['document_chunk_id']:r for r in document_pages}
    links = document_links or {}
    doc_time = response.pop('_document_retrieved_at',None)
    citations, used = [], set()
    for raw in response.get('citations', [])[:8]:
        cid = str(raw.get('id') or '')[:40]
        if not cid or cid in used:continue
        used.add(cid)
        chunk = documents.get(raw.get('document_chunk_id'))
        url = safe_url(raw.get('url'));matched = retrieved.get(url)
        source = {'id':cid,'number':len(citations)+1,'title':str(raw.get('title') or '')[:300],
                  'claim':str(raw.get('claim') or '')[:500],
                  'support_level':raw.get('support_level') if raw.get('support_level') in {'bibliographic_only','method_description','visible_page_or_table'} else 'not_assessed',
                  'access_limitation':str(raw.get('access_limitation') or '')[:500]}
        if chunk:
            quote=str(raw.get('supporting_quote') or '')[:1000]
            quote_match=bool(len(normal(quote))>=8 and normal(quote) in normal(chunk['text']))
            link=links.get(chunk['document_chunk_id'],{})
            source.update(origin='document',status='document_retrieved',title=chunk['title'],
                          url=safe_url(link.get('url')) or '',page_url=link.get('page_url',''),
                          document_chunk_id=chunk['document_chunk_id'],file_sha256=chunk['file_sha256'],
                          pdf_page=chunk['pdf_page'],printed_page=chunk.get('printed_page'),
                          locator=f"PDF p. {chunk['pdf_page']}"+(f" · printed p. {chunk['printed_page']}" if chunk.get('printed_page') else ''),
                          supporting_quote=quote,quote_match=quote_match,retrieved_at=doc_time,
                          limitation='Exact quote matched the retrieved page text; interpretation, table columns and applicability require engineering review.' if quote_match else 'The proposed quote did not match this retrieved page; claim support is incomplete.',
                          page_link_verified=bool(link.get('page_link_verified')))
            if not quote_match:source['support_level']='not_assessed'
        else:
            source.update(origin='web',url=url if matched else '',locator=str(raw.get('locator') or '')[:300],
                          status='retrieved' if matched else 'unverified_url_rejected',
                          retrieved_at=matched.get('retrieved_at') if matched else None,
                          retrieval_title=matched['title'] if matched else '',
                          limitation='URL returned by retrieval; claim, full text and page locator still require engineering review.' if matched else 'AI URL was not returned by the retrieval tool; no hyperlink is shown.')
        citations.append(source)
    response['citations']=citations
    by_id={c['id']:c for c in citations if c['status'] in {'retrieved','document_retrieved'}}
    response['assumptions']=response.get('assumptions',[])[:20]
    for point in response.get('points',[])+response.get('factors',[])+response['assumptions']:
        ids=list(dict.fromkeys(str(i) for i in point.get('source_ids',[]) if str(i) in by_id))
        point['source_ids']=ids;point['citations']=[by_id[i] for i in ids]
        point['citation_status']='retrieved_sources' if ids else 'no_external_evidence'
        if point.get('basis') not in {'project_data','engineering_hypothesis','source_supported'}:point['basis']='engineering_hypothesis'
        if point['basis']=='source_supported' and not any(by_id[i]['support_level'] in {'method_description','visible_page_or_table'} for i in ids):point['basis']='unsupported'
        point['needs_review']=point['basis']!='project_data'
    response['summary_source_ids']=[i for i in response.get('summary_source_ids',[]) if i in by_id]
    required={str(f['id']) for f in response.get('factors',[]) if f.get('id')}
    recorded={str(a.get('id')) for a in response['assumptions']}
    response['assumption_coverage']={'status':'complete' if required<=recorded else 'incomplete','missing_factor_ids':sorted(required-recorded)}
    response['citation_contract']='analyst-citations-2-documents'
    return response
