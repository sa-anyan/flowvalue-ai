"""Independent local PDF fixtures; no copyrighted source content is in these tests."""
import hashlib
import json
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, DictionaryObject, DecodedStreamObject
from fastapi.testclient import TestClient

from backend.blocks import reference_library as library
from backend.blocks.analyst_citations import validate_citations


def fixture_library(tmp_path,monkeypatch):
    writer=PdfWriter();page=writer.add_blank_page(400,500)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    content=DecodedStreamObject();content.set_data(b'BT /F1 12 Tf 20 460 Td (REFERENCE TEST 7) Tj 0 -30 Td (Piping 0.02-0.04 of purchased equipment cost) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(content)
    pdf=tmp_path/'independent.pdf'
    with pdf.open('wb') as stream:writer.write(stream)
    digest=hashlib.sha256(pdf.read_bytes()).hexdigest()
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps({'documents':[{'path':str(pdf),'sha256':digest,'title':'Independent fixture','web_url':'https://1drv.ms/b/test-reference'}]}))
    monkeypatch.setenv('FLOWVALUE_REFERENCE_MANIFEST',str(manifest));monkeypatch.setenv('FLOWVALUE_CLOUD','false')
    library.build_index(manifest)
    return manifest,pdf,digest


def test_pdf_retrieval_preserves_source_identity_page_and_table_text(tmp_path,monkeypatch):
    _,_,digest=fixture_library(tmp_path,monkeypatch)
    result=library.retrieve('capex','piping')
    page=result['pages'][0]
    assert page['pdf_page']==1 and page['printed_page']==7
    assert page['file_sha256']==digest and '0.02-0.04' in page['text']
    assert 'web_url' not in page and 'path' not in page
    assert result['links'][page['document_chunk_id']]['url']=='https://1drv.ms/b/test-reference'
    assert result['links'][page['document_chunk_id']]['page_url'].endswith('/pages/1')
    assert len(PdfReader(BytesIO(library.read_reference_page(digest,1))).pages)==1


def test_changed_document_and_wrong_hash_fail_closed(tmp_path,monkeypatch):
    manifest,pdf,_=fixture_library(tmp_path,monkeypatch)
    pdf.write_bytes(pdf.read_bytes()+b'changed')
    assert library.retrieve('capex')['pages']==[]
    with pytest.raises(ValueError):library.build_index(manifest)


def test_document_quote_and_ids_are_checked_against_actual_retrieval(tmp_path,monkeypatch):
    _,_,digest=fixture_library(tmp_path,monkeypatch)
    context=library.retrieve('capex','piping');page=context['pages'][0]
    response={'citations':[{'id':'S1','document_chunk_id':page['document_chunk_id'],'url':'https://invented.example/','supporting_quote':'Piping 0.02-0.04 of purchased equipment cost','support_level':'visible_page_or_table'}],
              'points':[{'basis':'source_supported','source_ids':['S1']}], 'factors':[], 'questions':[]}
    result=validate_citations(response,context['pages'],context['links']);citation=result['citations'][0]
    assert citation['quote_match'] is True and citation['status']=='document_retrieved'
    assert citation['url']=='https://1drv.ms/b/test-reference'
    assert citation['file_sha256']==digest
    citation['supporting_quote']='Invented value 90%'
    second={'citations':[citation],'points':[{'basis':'source_supported','source_ids':['S1']}]}
    checked=validate_citations(second,context['pages'],context['links'])
    assert checked['citations'][0]['quote_match'] is False
    assert checked['points'][0]['basis']=='unsupported'


def test_exact_page_endpoint_rejects_unknown_documents_and_cloud_access(tmp_path,monkeypatch):
    _,_,digest=fixture_library(tmp_path,monkeypatch)
    from backend.api import app as api
    monkeypatch.setattr(api,'CLOUD',False)
    with TestClient(api.app,base_url='http://localhost') as client:
        r=client.get(f'/api/catalogue/reference-documents/{digest}/pages/1')
        assert r.status_code==200 and r.content.startswith(b'%PDF')
        assert client.get(f'/api/catalogue/reference-documents/{digest}/pages/2').status_code==404
        assert client.get('/api/catalogue/reference-documents/'+'0'*64+'/pages/1').status_code==404
        monkeypatch.setattr(api,'CLOUD',True)
        assert api.reference_document_page
        with pytest.raises(Exception) as error:api.reference_document_page(digest,1)
        assert error.value.status_code==403
