"""Reproduce the cross-file evidence matrix from saved synthetic fixtures.
No AI, project persistence or historical numerical-result cache is involved.
"""
from pathlib import Path
import csv,json,runpy,sys,hashlib
r=Path(__file__).resolve().parents[6];sys.path.insert(0,str(r))
t=runpy.run_path(str(r/'backend/tests/test_sizing_cross_file.py'))
load=t['load'];sizing=t['sizing'];stream=t['stream'];derive=t['derive'];parse=t['parse'];derive_size=t['derive_size']
formats=t['FORMATS'];variants=t['VARIANTS'];fixture=t['FIXTURES']
# Reuse only this experiment's source extraction, not project/AI/cost results.
reports={f.name:load(f.name) for f in sorted(fixture.iterdir()) if f.suffix in ['.xlsx','.xlsm','.xls']}
rows=[]
expected={'gas_compression':(82.33066173777114,'kW'),'pump_duty':(.2298895010734333601697918125,'1000 US_gpm_psi'),'exchanger_area':(10,'m2'),'vaporizer_area':(12.5,'m2')}

def one(name,method,case='equivalent',boolean=None):
 report=reports[name];spec=sizing(report,method,efficiency=1e-320 if case=='overflow' else .5,gauge=case=='gauge')
 if boolean is not None:spec['stream_key']=stream(report,'H-IN')['key']
 entity=next(e for e in report['entities'] if e['key']==spec['stream_key'])
 observations=[{k:v.get(k) for k in ['id','property','label','sheet','cell','header_cells','original_value','original_unit','normalized_value','normalized_unit','status','note']} for v in entity['values']]
 want_rejection=case in ['boolean','overflow','missing_units']
 exp,unit=expected[method];actual=None;error='';audit={}
 try:actual,unit,audit=derive_size({'sizing':spec},report)
 except ValueError as exc:error=str(exc)
 status='PASS' if (bool(error) if want_rejection else actual is not None and abs(actual-exp)<=abs(exp)*5e-12) else 'FAIL'
 if case=='gauge':
  try:derive(sizing(report,method),report)
  except ValueError:pass
  else:status='FAIL';error+='; missing atmosphere was not rejected'
 rows.append(dict(source_file=name,source_format=name.rsplit('.',1)[1],case=case,source_field_names=json.dumps([v['label'] for v in observations]),extracted_and_normalized_values=json.dumps(observations),explicit_test_inputs=json.dumps(spec['parameters']),calculation_method=method,expected='explicit rejection' if want_rejection else str(exp),actual=error or str(actual),output_unit=unit,absolute_difference='' if actual is None or want_rejection else abs(actual-exp),relative_difference='' if actual is None or want_rejection else abs(actual-exp)/abs(exp),relative_tolerance='' if want_rejection else 5e-12,status=status,source_evidence=json.dumps(audit.get('source_evidence',[])),notes='Method and assumptions are explicit synthetic test inputs, not AI identification. Gauge case uses explicitly supplied 1 bar atmosphere.' if case=='gauge' else 'Boolean source cell is '+str(boolean) if case=='boolean' else ''))
for ext in formats:
 for variant in variants:
  for method in expected:one(variant+'.'+ext,method)
 for boolean in [True,False]:
  for method in ['exchanger_area','vaporizer_area']:one('rows_bool_'+str(boolean).lower()+'.'+ext,method,'boolean',boolean)
 one('rows.'+ext,'pump_duty','overflow')
 one('rows_gauge.'+ext,'gas_compression','gauge')
 for method in ['exchanger_area','vaporizer_area']:one('rows_missing_units.'+ext,method,'missing_units')
for ext in ['csv','pdf','docx','json','dwxml','png','xlsb']:
 try:parse(b'not an engineering workbook','synthetic.'+ext)
 except ValueError as exc:error=str(exc)
 else:error='ERROR: unexpectedly accepted'
 row={k:'' for k in rows[0]};row.update(source_file='synthetic.'+ext,source_format=ext,case='unsupported_active_path',calculation_method='NONE',expected='unsupported; reject explicitly',actual=error,status='BLOCKED',notes='No active ingestion adapter; rejection asserted by test, not counted as engineering compatibility.')
 rows.append(row)
p=r/'docs/verification/phase1/sizing/cross_file_compatibility_matrix.csv'
with p.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
e=Path(__file__).parent
(e/'fixture_manifest.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in fixture.iterdir() if f.suffix in ['.xlsx','.xlsm','.xls']},indent=2)+'\n')
(e/'matrix_summary.json').write_text(json.dumps({s:sum(row['status']==s for row in rows) for s in ['PASS','FAIL','BLOCKED']},indent=2)+'\n')
print({s:sum(row['status']==s for row in rows) for s in ['PASS','FAIL','BLOCKED']})
