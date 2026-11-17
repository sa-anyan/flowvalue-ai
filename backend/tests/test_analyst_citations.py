import copy
import json
from unittest.mock import patch

from backend.blocks.analyst_citations import retrieved_sources, validate_citations
from backend.blocks.analyst import analyse
from backend.orchestration.provider import EngineeringProvider


def raw_reply():
    return {'summary':'Synthetic summary', 'summary_source_ids':['s1'],
            'citations':[{'id':'s1','url':'https://example.org/retrieved','title':'Actual retrieved page','locator':'Section 2','claim':'A generic method'},
                         {'id':'fake','url':'https://made-up.example/','title':'Fabricated','locator':'Table 999','claim':'Unsupported claim'}],
            'points':[{'title':'Method','text':'A method','why':[],'would_change_if':[], 'evidence':[], 'source_ids':['s1','fake'],'basis':'source_supported'},
                      {'title':'Unsupported','text':'No proof','source_ids':['fake'],'basis':'source_supported'}],
            'factors':[], 'questions':[]}


def test_unretrieved_and_unsafe_urls_are_never_hyperlinks():
    response=raw_reply();response['_retrieved_sources']=[{'url':'https://example.org/retrieved','title':'Retrieved'}]
    checked=validate_citations(response)
    assert checked['citations'][0]['status']=='retrieved'
    assert checked['citations'][1]['url']==''
    assert checked['points'][0]['source_ids']==['s1']
    assert checked['points'][1]['basis']=='unsupported'
    assert checked['points'][1]['citation_status']=='no_external_evidence'
    assert checked['summary_source_ids']==['s1']
    for url in ['javascript:alert(1)','file:///tmp/source','https://user:password@example.org/']:
        response=raw_reply();response['citations'][0]['url']=url
        assert validate_citations(response)['citations'][0]['url']==''


def test_provider_tools_are_the_only_provenance_authority():
    reply=raw_reply();reply['_retrieved_sources']=[{'url':'https://made-up.example/','title':'Spoofed model field'}]
    raw={'status':'completed','output':[{'type':'web_search_call','action':{'sources':[{'url':'https://example.org/retrieved','title':'Tool source'}]}},
         {'type':'message','content':[{'type':'output_text','text':json.dumps(reply),'annotations':[]}]}]}
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*args):return json.dumps(raw).encode()
    class Opener:
        calls=[]
        def open(self,request,**kwargs):
            self.calls.append(json.loads(request.data));return Response()
    opener=Opener();provider=EngineeringProvider.__new__(EngineeringProvider);provider.model='test';provider._key='test-only'
    with patch('backend.orchestration.provider.build_opener',return_value=opener):
        result=provider._generate(instructions='Test',context={'analyst_version':'test'},schema={},cited=True)
    assert len(opener.calls)==1
    assert opener.calls[0]['max_tool_calls']==2
    assert result['_retrieved_sources'][0]['url']=='https://example.org/retrieved'
    assert result['_retrieved_sources'][0]['retrieved_at']
    assert validate_citations(result)['citations'][1]['url']==''


def test_provider_annotations_are_retained_and_cache_does_not_research_again():
    tool_raw={'output':[{'type':'message','content':[{'type':'output_text','annotations':[{'type':'url_citation','url':'https://example.org/retrieved','title':'Citation'}]}]}]}
    assert retrieved_sources(tool_raw)[0]['url']=='https://example.org/retrieved'
    class Provider:
        calls=0
        def generate(self,**kwargs):raise AssertionError('Use cited method')
        def generate_cited(self,**kwargs):
            self.calls+=1
            result=raw_reply();result['_retrieved_sources']=retrieved_sources(tool_raw);return result
    class Cache:
        value=None
        def cached(self,context,fn):
            if self.value is None:self.value=fn();return copy.deepcopy(self.value),False
            return copy.deepcopy(self.value),True
    provider=Provider();cache=Cache();state={'effective_report':{'entities':[]}}
    first=analyse(state,'equipment',cache,provider);second=analyse(state,'equipment',cache,provider)
    assert provider.calls==1
    assert first['points'][0]['citations'][0]['url']==second['points'][0]['citations'][0]['url']
    assert first['points'][0]['citations'][0]['retrieved_at']==second['points'][0]['citations'][0]['retrieved_at']
    assert second['cached'] is True
    assert state=={'effective_report':{'entities':[]}}


def test_bibliographic_identity_cannot_be_labelled_claim_support():
    response=raw_reply();response['citations'][0]['support_level']='bibliographic_only'
    response['_retrieved_sources']=[{'url':'https://example.org/retrieved','title':'Book identity','retrieved_at':'2026-11-17T08:00:00+00:00'}]
    checked=validate_citations(response)
    assert checked['points'][0]['basis']=='unsupported'
    assert checked['citations'][0]['url']=='https://example.org/retrieved'
    assert checked['citations'][0]['retrieved_at']=='2026-11-17T08:00:00+00:00'
