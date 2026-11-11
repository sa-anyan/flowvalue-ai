"""Consolidated METHOD-001 evidence; reuse prior references and test logs."""
import ast,csv,hashlib,inspect,json,math,platform,sys,xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
r=Path(__file__).resolve().parents[5];sys.path.insert(0,str(r));out=Path(__file__).resolve().parents[1];e=out/'evidence'
from backend.engineering_sizing.registry import METHODS,PARAMETER_UNITS
from backend.engineering_sizing.adapter import derive
from backend.orchestration.sizing import derive_size
from backend.equipment_costing.unit_conversion.bridges.service import RECIPES
from backend.equipment_costing.unit_conversion.bridges import mechanical,production_sizing,liquid
from backend.equipment_costing.unit_conversion import convert,identify_unit


def csvrows(path):return list(csv.DictReader((r/path).open()))
def write(name,rows):
 with (out/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
refs=json.loads((r/'backend/tests/fixtures/sizing_verification/references.json').read_text());extra=json.loads((e/'additional_references.json').read_text())
oldmethods=csvrows('docs/verification/phase1/sizing/sizing_methods_register.csv')
app=csvrows('docs/verification/phase1/closure/sizing_applicability_register.csv');hist=csvrows('docs/audits/phase0/engineering_methods_register.csv')
assert len(hist)==248 and len(refs)==len(METHODS)==12
sourcehistory=json.loads((r/'docs/verification/phase1/closure/evidence/source_history.json').read_text())
closure=csvrows('docs/verification/phase1/closure/sizing_source_provenance_register.csv')
# Contemporary source hashes include dirty working-tree content; HEAD alone is
# intentionally not treated as a sufficient implementation version.
paths=set()
for folder in ['backend/engineering_sizing','backend/equipment_costing/unit_conversion']:
 paths.update(p for p in (r/folder).rglob('*.py') if ' 2' not in p.name and '__pycache__' not in p.parts)
paths.update([r/'backend/orchestration/sizing.py',r/'backend/blocks/equipment/calculation.py',r/'backend/tests/fixtures/sizing_verification/references.json',e/'additional_references.json',r/'backend/tests/test_method_acceptance.py'])
manifest={str(p.relative_to(r)):digest(p) for p in sorted(paths)}
(e/'implementation_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# G1 criterion transcription is reused verbatim from the retained official DOCX
# extraction, not synthesized from implementation claims.
paras=json.loads((r/'docs/audits/phase0/evidence/g0_reconciliation/roadmap_paragraphs.json').read_text())
(e/'official_G1_criteria.json').write_text(json.dumps([x for x in paras if 117<=x['paragraph']<=122],indent=2)+'\n')
source_by={x['method_id']:x for x in closure}
# Replacement references: original implementation publication origin remains unknown.
source_rows=[];app_rows=[];repro=[];trace=[]
for c in refs:
 mid=c['method'];d=METHODS[mid];old=next(x for x in oldmethods if x['method_id']==mid);prior=source_by[mid];a=next(x for x in app if x['method_id']==mid)
 file=Path(inspect.getsourcefile(d['calculator'])).resolve();function=d['calculator'].__name__
 replacement=prior['independent_source_publication_edition']
 sourceurl=a['source_url']
 if mid=='gas_compression':
  replacement='NASA ideal compressor; Fluids author isentropic_work_compression derivation; Joe Honeywell/JM Campbell May2009 constant-property approximation discussion'
  sourceurl='https://www.grc.nasa.gov/www/k-12/airplane/compth.html ; https://fluids.readthedocs.io/fluids.compressible.html ; https://www.jmcampbell.com/tip-of-the-month/2009/05/the-sensitivity-of-k-values-on-compressor-performance/'
 source_rows.append({'method_id':mid,'callable':str(file.relative_to(r))+':'+function,'currently_advertised':'Production catalogue /api/catalogue; preliminary screening as documented, not certified detailed design','governing_equation':old['equation'],'original_publication_origin':'UNKNOWN — not recovered','code_history':sourcehistory[mid]['earliest_add_commit'],'accepted_replacement_reference':replacement,'reference_locator':('Fluids author documentation: isentropic_work_compression equation/derivation and published example; JM Campbell May2009 sensitivity discussion' if mid=='gas_compression' else prior['verified_section_or_equation']),'reference_url':sourceurl,'coefficient_unit_review':'R=exact kB*NA with kg/kmol and kPa/bar factors; US gallon/psi exact definitions; 60/3600/1000 unit factors; others conservation/geometry identities','independent_reference_acceptance':'PASS — bounded preliminary relationship or explicit conservation derivation','historical_source_acceptance':'UNKNOWN; not fabricated or needed to identify replacement reference','numerical_evidence':'304 native cases reused from UNIT-003 targeted.xml; compressor numerical regression and new reference cases focused.xml','method_source_sha256':digest(file),'method_specific_rtol':c['relative_tolerance'],'absolute_tolerance':c['absolute_tolerance'],'engineering_uncertainty':'Not bounded by numerical tolerance; property/assumption/model applicability remains separate'})
 domain=a['operating_conditions_and_domain'];limits=a['limitations_and_not_for_use']
 if mid=='gas_compression':
  limits+='; Z representative of path, not generally inlet Z; effective k and Z do not give an EOS isentrope when properties vary; consistent total/static states required; numerical k<=2 is not a certified physical envelope'
 if mid=='ion_exchange_capacity':limits+='; ionic-equivalent load means targeted load removed over the cycle; resin-bed fraction is gross-vessel occupancy, not resin porosity'
 if mid=='phase_change_duty':limits+='; nonnegative duty magnitude; omitted sensible delta_h defaults to zero, a saturation/no-sensible-change assumption, not a full signed plant balance'
 app_rows.append({'method_id':mid,'declared_scope':'Existing preliminary screening; unchanged','required_process_properties':a['required_inputs'],'required_design_assumptions':a['assumptions'],'supported_relationship':a['governing_equation'],'code_domain_not_operating_envelope':domain,'unsupported_conditions':limits,'must_remain_unresolved_when':a['additional_process_inputs_or_evidence']+' are absent/unqualified for the intended application; no inference of a validated design','professional_review':a['required_margins_or_additional_checks'],'applicability_record_acceptance':'PASS — sufficient as a conditional screening identity; not acceptance of any actual project inputs','enforcement_limitation':'Scalar guards and warnings do not independently verify supplied phase/properties/roles or professional design applicability'})
 # Collect source trace, not rerun 304 tests. One new fixture observation per ID
 # establishes exactly what audit information survives the supported adapter.
 report={'entities':[{'key':'s','kind':'material','identifier':'REFERENCE-'+mid,'values':[{'id':'METHOD-001:'+mid+':B3','property':d['input'],'normalized_value':c['value'],'normalized_unit':d['unit'],'status':'verified','workbook':'isolated METHOD-001 reference, not a real plant','sheet':'Reference','cell':'B3'}]}]}
 spec={'method':mid,'stream_key':'s','parameters':c['parameters']}
 result=derive(spec,report)
 assert result[1]==c['unit'] and math.isclose(result[0],float(c['expected']),rel_tol=c['relative_tolerance'],abs_tol=c['absolute_tolerance'])
 trace.append({'method':mid,'report':report,'sizing_spec':spec,'returned_result':result,'runtime_method_version_present':any(k in result[2] or k in result[2].get('calculation',{}) for k in ['method_version','software_version','method_source_sha256']),'external_source_hash':digest(file),'scope':'Synthetic numerical reference trace; not a workbook ingestion or persistence test'})
 repro.append({'case_id':'NATIVE-'+mid,'method_id':mid,'input_value':c['value'],'input_unit':d['unit'],'parameters':json.dumps(c['parameters']),'parameter_units':json.dumps({k:PARAMETER_UNITS[k] for k in c['parameters']}),'independent_expected':c['expected'],'actual':result[0],'unit':result[1],'relative_tolerance':c['relative_tolerance'],'absolute_tolerance':c['absolute_tolerance'],'independent_derivation':c['hand_calculation'],'validity_limits':limits,'evidence':'Original independent fixture/304 reused; new source/trace-only nominal capture','method_source_sha256':digest(file),'status':'PASS'})

extras={
 'volume_residence':(derive_size,'backend/orchestration/sizing.py','Same hold-up identity V=Q*t/f as vessel_hold_up; independent residence conservation derivation','Actual same-state Q,positive residence time and working fraction; no validated automatic sizing','Reachable legacy route; primary-flow/output positivity not enforced as in the native registry; negative volume counterexample recorded'),
 'mass_residence':(derive_size,'backend/orchestration/sizing.py','Same hold-up identity V=(massflow/density)*t/f; qualified density and residence conservation','Same-phase mass flow and qualified density, residence time and working fraction','Reachable legacy route; primary-flow/output positivity not enforced as in the native registry; negative volume counterexample recorded'),
 'vessel_mass':(mechanical.evaluate,'backend/equipment_costing/unit_conversion/bridges/mechanical.py','Geometry: annular cylinder volume times density plus explicitly supplied head/auxiliary mass','Supplied D,t,L,material density and head/auxiliary mass; no thickness or code calculation','No head-shape prediction, pressure code, corrosion allowance or automatic material selection'),
 'vessel_productivity':(production_sizing.vessel_productivity,'backend/equipment_costing/unit_conversion/bridges/production_sizing.py','Productivity definition: production/volumetric productivity, allocation and working/gross conversion','Explicit productivity applicable to this process/product and same working-volume basis','No kinetics, yield, gas-transfer or growth-rate prediction; allocation is not invented'),
 'mixing_power':(liquid.evaluate,'backend/equipment_costing/unit_conversion/bridges/liquid.py','Definition of power density times the same gross/design volume basis','Explicit design-volume power density, flow/residence/working fraction; unit-compatible allocation','No empirical power density prescribed; working-volume literature data needs basis conversion; no agitator mechanical/performance prediction')}
for mid,(fn,file,ref,required,limits) in extras.items():
 c=next(x for x in extra if x['method']==mid)
 source_rows.append({'method_id':mid,'callable':file+':'+fn.__name__,'currently_advertised':('Reachable legacy derive_size branch; not deprecated; separate integration implementation' if mid in {'mass_residence','volume_residence'} else 'Active equipment bridge RECIPES entry; preliminary supplied-assumption estimator, not deprecated'),'governing_equation':c['derivation'],'original_publication_origin':'UNKNOWN — no original implementation citation established','code_history':'Not asserted for supplemental helpers','accepted_replacement_reference':ref,'reference_locator':'Independent conservation/geometry/definition derivation in critical_reference_derivations.md; no uninspected original publication claimed','reference_url':'Definition/conservation derivation; NIST density and dimensional conventions reused','coefficient_unit_review':'No empirical coefficient supplied: thickness, density, productivity and power-density are explicit inputs','independent_reference_acceptance':'PASS — bounded supplied-input estimator, not predictive equipment design','historical_source_acceptance':'UNKNOWN','numerical_evidence':'METHOD-001 focused.xml; additional_references.json','method_source_sha256':digest(r/file),'method_specific_rtol':c['rtol'],'absolute_tolerance':c['atol'],'engineering_uncertainty':'No validated empirical design uncertainty; input assumptions require evidence'})
 app_rows.append({'method_id':mid,'declared_scope':'Active preliminary supplied-input estimator; unchanged arithmetic','required_process_properties':json.dumps(c['inputs']),'required_design_assumptions':required,'supported_relationship':c['derivation'],'code_domain_not_operating_envelope':('Legacy density/time/fraction checks exist, but negative primary sizing flow and output are not rejected' if mid in {'mass_residence','volume_residence'} else 'Positive finite inputs; applicable fraction <=1; heads may be explicit0'),'unsupported_conditions':limits,'must_remain_unresolved_when':'Source-specific input definitions/basis or required values are missing','professional_review':'Independently qualify geometry/material/productivity/power-density basis for actual service','applicability_record_acceptance':('PARTIAL — limits documented; active legacy validation counterexample remains' if mid in {'mass_residence','volume_residence'} else 'PASS — conditional identity/estimator only'),'enforcement_limitation':'No process performance/model-suitability validator is claimed'})

def cv(v,u,t=None):
 if v=='quantity':return identify_unit(u).quantity
 x=convert(v,u,t)
 if x.value is None:raise ValueError('; '.join(x.issues))
 return x.value
for c in extra:
 mid=c['method']
 if mid=='vessel_mass':result=mechanical.evaluate(c['inputs']);file=extras[mid][1]
 elif mid=='vessel_productivity':result=production_sizing.vessel_productivity(c['inputs']);file=extras[mid][1]
 elif mid=='mixing_power':result=liquid.evaluate(mid,c['value'],c['source_unit'],c['inputs'],cv);file=extras[mid][1]
 elif mid in {'mass_residence','volume_residence'}:
  prop='mass_flow' if mid=='mass_residence' else 'volume_flow'
  report={'entities':[{'key':'s','values':[{'id':'legacy-ref','property':prop,'normalized_value':c['value'],'normalized_unit':c['source_unit'],'status':'verified'}]}]}
  result=derive_size({'sizing':{'method':mid,'stream_key':'s',**c['inputs']}},report);file='backend/orchestration/sizing.py'
 else:result=METHODS[mid]['calculator'](c['value'],c['inputs']);file='backend/engineering_sizing/compression.py'
 assert math.isclose(result[0],float(c['expected']),rel_tol=c['rtol'],abs_tol=c['atol'])
 repro.append({'case_id':c['id'],'method_id':mid,'input_value':c.get('value','Supplied geometry/productivity parameters'),'input_unit':c.get('source_unit','kg/h' if mid=='gas_compression' else 'named SI parameters'),'parameters':json.dumps(c['inputs']),'parameter_units':'Named native parameters: all units in keys/derivation','independent_expected':c['expected'],'actual':result[0],'unit':result[1],'relative_tolerance':c['rtol'],'absolute_tolerance':c['atol'],'independent_derivation':c['derivation'],'validity_limits':next(x['unsupported_conditions'] for x in app_rows if x['method_id']==mid),'evidence':'METHOD-001 focused.xml; no production code used as expected-value oracle','method_source_sha256':digest(r/file),'status':'PASS'})
write('sizing_method_reference_acceptance.csv',source_rows)
write('method_applicability_acceptance.csv',app_rows)
write('independent_reproducibility_matrix.csv',repro)
(e/'trace_probes.json').write_text(json.dumps(trace,indent=2)+'\n')
# Categorize all historical candidates without equating functions to methods.
# No row is silently deprecated; current API/recipe declarations remain active.
scope=[]
for row in hist:
 loc=row['python_location'];name=row['calculation'];family=row['equipment_family'];alias=''
 if row['method_id'].startswith('ENG-SIZE-'):
  cat='Genuine engineering method: historical register alias';alias=name;stage='P1';state='Active registered preliminary screening'
 elif family=='engineering_sizing':
  cat='Numerical/adapter helper' if name in ['derive','gas_inputs','compute'] or '/registry.py' in loc else 'Genuine engineering implementation: duplicate of registered method IDs'
  stage='P1';state='Executable; native preliminary scope unchanged'
 elif '/unit_conversion/' in loc:
  cat='Unit conversion/contextual derivation or adapter'
  if '/mechanical.py' in loc:alias='vessel_mass';cat='Genuine engineering estimator: current record below'
  if '/production_sizing.py' in loc:alias='vessel_productivity';cat='Genuine engineering estimator: current record below'
  stage='P1';state='Active finite converter/context workflow; source-specific preconditions apply'
 elif family=='ingestion':cat='Ingestion/interface normalization';stage='P1/P2 Engineer2';state='Separate owner; recorded Boolean/L/s defects remain open'
 elif family=='equipment_costing':
  cat='Cost correlation/source model or costing adapter';stage='P3';state='Implemented/provisional/blocked source states preserved; not independently validated by METHOD-001'
  if '/cost_to_future/' in loc:cat='Historical cost-basis economic transformation';stage='P3/P4';state='Dated source/index applicability separate from physical unit conversion'
 elif family=='currency_conversion':cat='Currency/context economic conversion';stage='P4';state='Implemented dated rate arithmetic; source observation acceptance separate'
 elif family=='scenarios_and_uncertainty':cat='Sampling/statistical/orchestration helper';stage='P4/scenario validation';state='Executable helper; not a standalone physical design method'
 else:cat='Economic method or economic adapter';stage='P4';state='Existing implemented policy/calculation; no Phase4 acceptance implied'
 scope.append({'scope_id':row['method_id'],'calculation':name,'location':loc,'classification':cat,'declared_current_status':state,'counts_as_distinct_P1_engineering_method':False,'canonical_alias_if_known':alias,'phase_owner':stage,'G1_criteria':'117-122 for P1; separate P3/P4 scientific validation for costs/economics','evidence':'P0 248-candidate inventory reconciled to current METHODS and RECIPES; this is classification, not source approval'})
for row in source_rows:
 scope.append({'scope_id':'CURRENT:'+row['method_id'],'calculation':row['method_id'],'location':row['callable'],'classification':'Genuine engineering calculation method/estimator','declared_current_status':row['currently_advertised'],'counts_as_distinct_P1_engineering_method':True,'canonical_alias_if_known':row['method_id'],'phase_owner':'P1 Engineer1','G1_criteria':'117 references/applicability;118 critical numerics;119 unsupported;120 lineage/version;121 tolerance;122 reproducibility','evidence':'sizing_method_reference_acceptance.csv; method_applicability_acceptance.csv; independent_reproducibility_matrix.csv'})
for name,loc,cat in [('average_power','backend/equipment_costing/unit_conversion/relationships.py','Contextual physical derivation E/time'),('residence_time','backend/equipment_costing/unit_conversion/relationships.py','Contextual physical derivation V/Q'),('normalize_parameters','backend/equipment_costing/unit_conversion/sizing_parameters.py','Unit normalization helper')]:
 scope.append({'scope_id':'UNIT003:'+name,'calculation':name,'location':loc,'classification':cat,'declared_current_status':'Active bounded UNIT-003 helper; unchanged','counts_as_distinct_P1_engineering_method':False,'canonical_alias_if_known':'','phase_owner':'P1 units','G1_criteria':'UNIT-003 retained evidence; not a new equipment design method','evidence':'UNIT-003 regression_summary.json / conversion_independent_verification.csv'})
write('production_calculation_scope.csv',scope)
# Check directly which bodies changed since UNIT-003's verified source snapshot.
u3=json.loads((r/'docs/verification/phase1/units/UNIT-003/evidence/before_hashes.json').read_text())
compare={str(p.relative_to(r)):digest(p)==u3.get(str(p.relative_to(r))) for p in (r/'backend/engineering_sizing').glob('*.py')}
# Evidence coverage counts come from retained JUnit testcases, not sums of tickets.
unit3xml=r/'docs/verification/phase1/units/UNIT-003/evidence/targeted.xml'
root=ET.parse(unit3xml).getroot();native=[x for x in root.iter('testcase') if 'test_sizing_independent_verification' in x.get('classname','')]
assert len(native)==304 and not any(x.find('failure') is not None for x in native)
focused=ET.parse(e/'focused.xml').getroot();alltests=list(focused.iter('testcase'))
reuse={'native304':{'path':str(unit3xml.relative_to(r)),'sha256':digest(unit3xml),'tests':len(native),'failures':0,'scope':'Retained native 304 assertions. Arithmetic unchanged; compressor metadata-only annotation independently AST-checked and focused compressor rerun.'},'UNIT003':{'path':'docs/verification/phase1/units/UNIT-003/evidence/regression_summary.json','sha256':digest(r/'docs/verification/phase1/units/UNIT-003/evidence/regression_summary.json'),'distinct_passed_tests':3293,'scope':'Units and unmodified heat/pump/Boolean/R01: reused, not rerun'},'current_source_vs_UNIT003_before':compare,'fresh_tests':len(alltests),'fresh_failures':len(list(focused.iter('failure'))),'fresh_errors':len(list(focused.iter('error'))),'fresh_skips':len(list(focused.iter('skipped'))),'historical_full_backend':'UNIT-C01:3056 passed,5 Engineer2 failed,3 skips,367 subtests; not rerun or assumed corrected','deferred_engineer2_findings':['SIZE-XF01: XLS Boolean type lost in2 cases','SIZE-XF02: L/s reader normalization in3 cases'],'note':'No complete backend rerun; no external reviewer signoff asserted'}
(e/'evidence_reuse.json').write_text(json.dumps(reuse,indent=2)+'\n')
(e/'summary.json').write_text(json.dumps({'historical_candidates':len(hist),'scope_rows':len(scope),'registered_sizing_ids':12,'additional_active_estimators':3,'additional_legacy_engineering_branches':2,'distinct_P1_method_ids':17,'unique_core_callables':len({d['calculator'] for d in METHODS.values()}),'replacement_reference_acceptances':dict(Counter(x['independent_reference_acceptance'].split(' —')[0] for x in source_rows)),'applicability_record_acceptances':dict(Counter(x['applicability_record_acceptance'].split(' —')[0] for x in app_rows)),'reproduction_cases':len(repro),'new_focused_passed':len(alltests),'runtime_version_missing_method_ids':[x['method'] for x in trace if not x['runtime_method_version_present']],'legacy_boundary_failures':2,'combined_G1':'FAIL / not ready; Engineer1 readiness PARTIAL; shared integration blockers remain'},indent=2)+'\n')
print((e/'summary.json').read_text())
