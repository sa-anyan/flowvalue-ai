"""Read-only, page-level retrieval from an explicitly configured local document library.

Local OneDrive sync is the demo's document transport, not a cloud connector.
Only files in the private manifest are indexed. No uploaded scripts are executed.
"""
import hashlib
import json
import math
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

VERSION = 'reference-pages-1'
STOP = set('the and for with from that this into are not your more cost costs engineering chemical economics'.split())
STAGE_TERMS = {
 'capex':'plant cost estimating factors Table 3-4 piping insulation electrical instrumentation utilities contingency construction installation fluids solids',
 'opex':'manufacturing operating labour labor utilities maintenance raw materials Table 4-4',
 'equipment':'equipment cost estimating installation size capacity residence time vessel pump pressure temperature design',
 'revenue':'product sales value market research production quantity',
 'financial':'discounted cash flow interest depreciation working capital profitability',
}


def _manifest_path():
    if os.environ.get('FLOWVALUE_CLOUD','false').lower()=='true':return None
    value=os.environ.get('FLOWVALUE_REFERENCE_MANIFEST','').strip()
    return Path(value).expanduser().resolve() if value else None


def _tokens(value):
    return [w for w in re.findall(r'[a-z][a-z0-9-]{2,}',value.lower()) if w not in STOP]


def _printed_page(text):
    for line in text.splitlines()[:8]:
        line=line.strip()
        if not line:continue
        m=re.fullmatch(r'(\d{1,3})\s+CHEMICAL\s+ENGINEERING\s+ECONOMICS',line)
        if not m:m=re.fullmatch(r'[A-Z][A-Z ,;()\-/&]+\s+(\d{1,3})',line)
        if m:return int(m.group(1))
    return None


def _file_sha(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def build_index(manifest_path):
    """Explicit offline indexing; retain layout text so table rows stay aligned."""
    from pypdf import PdfReader
    manifest_path=Path(manifest_path).resolve()
    manifest=json.loads(manifest_path.read_text())
    pages=[];identities=[]
    for spec in manifest.get('documents',[]):
        path=Path(spec['path']).expanduser().resolve()
        if path.suffix.lower()!='.pdf' or not path.is_file():raise ValueError('Reference PDF unavailable')
        digest=_file_sha(path)
        if spec.get('sha256') and digest!=spec['sha256']:raise ValueError('Reference PDF hash mismatch; re-review the source')
        reader=PdfReader(path)
        if reader.is_encrypted:raise ValueError('Encrypted reference PDF is not indexed')
        identities.append({'path':str(path),'size':path.stat().st_size,'mtime_ns':path.stat().st_mtime_ns,'sha256':digest,'pages':len(reader.pages)})
        for index,page in enumerate(reader.pages,1):
            content=page.extract_text(extraction_mode='layout') or ''
            if not content.strip():continue
            # Complete pages are retained locally; selected context is bounded below.
            pages.append({'document_chunk_id':f'{digest[:16]}:page:{index}','document_id':digest,'file_sha256':digest,
                          'title':spec.get('title',path.name),'filename':path.name,'pdf_page':index,
                          'printed_page':_printed_page(content),'text':content,
                          'web_url':spec.get('web_url',''),'page_link_verified':bool(spec.get('page_link_verified',False)),
                          'page_url_template':spec.get('page_url_template','')})
    out={'version':VERSION,'identities':identities,'pages':pages}
    cache=Path(manifest.get('index_path') or manifest_path.with_name('page-index.json')).expanduser().resolve()
    cache.parent.mkdir(parents=True,exist_ok=True);cache.write_text(json.dumps(out));cache.chmod(0o600)
    _load.cache_clear()
    return {'documents':len(identities),'pages':len(pages),'index_path':str(cache)}


@lru_cache(maxsize=4)
def _load(path,stamp,index_stamp):
    manifest=json.loads(Path(path).read_text())
    cache=Path(manifest.get('index_path') or Path(path).with_name('page-index.json')).expanduser().resolve()
    data=json.loads(cache.read_text())
    if data.get('version')!=VERSION:raise ValueError('Reference index version mismatch')
    for identity in data['identities']:
        stat=Path(identity['path']).stat()
        if stat.st_size!=identity['size'] or stat.st_mtime_ns!=identity['mtime_ns']:
            raise ValueError('Reference PDF changed; re-index before using it')
    counts=[Counter(_tokens(page['text'])) for page in data['pages']]
    frequency=Counter()
    for tokens in counts:frequency.update(tokens.keys())
    data['_counts']=counts;data['_frequency']=frequency
    return data


def _library():
    path=_manifest_path()
    if not path:return None
    manifest=json.loads(path.read_text())
    cache=Path(manifest.get('index_path') or path.with_name('page-index.json')).expanduser().resolve()
    data=_load(str(path),path.stat().st_mtime_ns,cache.stat().st_mtime_ns)
    for identity in data['identities']:
        stat=Path(identity['path']).stat()
        if stat.st_size!=identity['size'] or stat.st_mtime_ns!=identity['mtime_ns']:raise ValueError('Reference PDF changed; re-index before using it')
    return data


def _page_url(page):
    # Never assume a OneDrive viewer accepts #page. Use a tested template only.
    template=page.get('page_url_template','')
    if page.get('page_link_verified') and template and '{page}' in template:
        return template.replace('{page}',str(page['pdf_page']))
    return page.get('web_url','')


def retrieve(stage,query='',references=(),limit=6,max_chars=25000):
    try:data=_library()
    except (OSError,ValueError,KeyError):
        return {'pages':[],'links':{},'notice':'Reference library unavailable or changed; document support cannot be claimed.'}
    if not data:return {'pages':[],'links':{},'notice':'No private reference library configured.'}
    terms=Counter(_tokens(STAGE_TERMS.get(stage,'')+' '+query))
    requested={(r.get('sha256'),r.get('pdf_page')) for r in references if isinstance(r,dict)}
    counts=data['_counts'];frequency=data['_frequency']
    ranked=[]
    for page,tokens in zip(data['pages'],counts):
        score=sum(min(tokens[t],4)*math.log(1+len(counts)/(1+frequency[t]))*min(weight,2) for t,weight in terms.items())
        if (page['file_sha256'],page['pdf_page']) in requested:score+=1000
        ranked.append((score,page))
    selected=[];links={};size=0
    for score,page in sorted(ranked,key=lambda r:r[0],reverse=True):
        if score<=0 or len(selected)>=limit:break
        # Do not send a truncated table as if it were a complete page.
        if len(page['text'])>10000 or size+len(page['text'])>max_chars:continue
        public={k:page[k] for k in ('document_chunk_id','document_id','file_sha256','title','filename','pdf_page','printed_page','text')}
        selected.append(public);size+=len(page['text'])
        links[page['document_chunk_id']]={'url':_page_url(page),'page_link_verified':page['page_link_verified'],'page_url':f"/api/catalogue/reference-documents/{page['file_sha256']}/pages/{page['pdf_page']}"}
    return {'pages':selected,'links':links,'notice':'Retrieved layout-preserving PDF pages from the configured read-only OneDrive sync. Graph images are not interpreted by text retrieval.'}


def read_reference_page(document_id,page_number):
    """Return one original source page for local, read-only evidence inspection."""
    from io import BytesIO
    from pypdf import PdfReader,PdfWriter
    data=_library()
    if not data:raise FileNotFoundError('No reference library configured')
    identity=next((r for r in data['identities'] if r['sha256']==document_id),None)
    if not identity or not isinstance(page_number,int) or not 1<=page_number<=identity['pages']:
        raise FileNotFoundError('Reference page not found')
    reader=PdfReader(identity['path']);writer=PdfWriter();writer.add_page(reader.pages[page_number-1])
    output=BytesIO();writer.write(output);return output.getvalue()
