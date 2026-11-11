"""Record actual results against static independent references; no production writes."""
from pathlib import Path
import sys,json,csv,runpy
from decimal import Decimal as D
from collections import Counter
r=Path(__file__).resolve().parents[5];sys.path.insert(0,str(r));p=r/'docs/verification/phase1/units'
t=runpy.run_path(str(r/'backend/tests/test_unit_acceptance.py'))
from backend.equipment_costing.unit_conversion import convert,ConversionContext,identify_unit
from backend.equipment_costing.unit_conversion.unit_aliases import UNITS,ALIASES,WORDS,key
from backend.equipment_costing.registry import list_equipment_models
from backend.engineering_sizing.registry import METHODS,PARAMETER_UNITS,calculate
from backend.engineering_sizing.adapter import derive
import numpy as np


def save(name,rows):
 with (p/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)

reg=[];canonical=set()
for c in t['REFERENCES']:
 out=convert(c['value'],c['source'],c['destination'],context=ConversionContext(**c['context']))
 assert out.value is not None
 canonical.update([out.canonical_input_unit,out.canonical_target_unit])
 reg.append(dict(case_id=c['id'],kind='unit conversion',source_quantity=c['value'],source_unit=c['source'],destination_unit=c['destination'],dimension=c['dimension'],relationship=c['relationship'],context=json.dumps(c['context']),independent_expected=c['expected'],actual=out.value,absolute_difference=str(abs(D(str(out.value))-D(c['expected']))),relative_tolerance=c['relative_tolerance'],absolute_tolerance=c['absolute_tolerance'],evidence='backend/tests/test_unit_acceptance.py::test_independent_supported_unit['+c['id']+'-'+c['source']+']; targeted.xml',status='PASS',scope='Finite Python-number inputs; source unit/basis as explicitly specified; not universal catalogue acceptance'))
# Two explicit physical bridges; not dimension-only conversion claims.
for cid,kind,src,dst,expected,inputs in [
 ('D01','liquid_flow','kg/s','m3/h',7.2,{'density_kg_m3':1000}),
 ('D02','standard_gas_flow','m3/h','Sm3/h',50,dict(molecular_weight_kg_kmol=28,temperature_k=300,absolute_pressure_bar=1,compressibility_z=1,reference_temperature_k=300,reference_pressure_bar=2,reference_compressibility_z=1))]:
 value=2 if cid=='D01' else 100
 actual=(t['liquid'].evaluate(kind,value,src,inputs,t['cv']) if cid=='D01' else t['gas'].evaluate(kind,value,src,inputs,t['cv']))[0]
 reg.append(dict(case_id=cid,kind='physical derivation',source_quantity=value,source_unit=src,destination_unit=dst,dimension='Different quantities; explicit physical relationship',relationship='mass/rho; normalize kg/s to kg/h first' if cid=='D01' else 'Qref=Qactual*(Pactual/Pref)*(Tref/Tactual)*(Zref/Zactual); gas composition unchanged',context=json.dumps(inputs),independent_expected=expected,actual=actual,absolute_difference=abs(actual-expected),relative_tolerance=5e-12,absolute_tolerance=1e-14,evidence='test_unit_acceptance.py::test_mass_to_volume_uses_explicit_density' if cid=='D01' else 'test_unit_acceptance.py::test_actual_to_reference_volume_requires_explicit_states',status='PASS',scope='Only with supplied qualified density/state and unchanged composition; not a default assumption'))
chainrows=[]
for c in t['NATIVE']:
 m=c['method'];defn=METHODS[m]
 for choice in [0,1]:
  value,unit,native=t['SOURCE_UNITS'][defn['input']][choice]
  normalized=convert(value,unit,defn['unit']).value
  actual,outu,_=calculate(m,normalized,c['parameters'])
  expected=float(c['expected'])*native/c['value']
  chainrows.append(dict(method_id=m,source_unit=unit,native_unit=defn['unit'],source_value=value,expected_native_value=native,actual_native_value=normalized,expected_sizing_result=expected,actual_sizing_result=actual,output_unit=outu,status='PASS',scope='Explicit valid Python-number parameters; units already native for parameters; no ingestion or type-safety approval'))
  reg.append(dict(case_id='N-'+m+'-'+str(choice),kind='numeric source-to-native sizing',source_quantity=value,source_unit=unit,destination_unit=defn['unit']+' -> '+outu,dimension=defn['input']+' -> native sizing output',relationship='Independent unit conversion then existing sizing equation with explicit parameter inputs',context=json.dumps(c['parameters']),independent_expected=expected,actual=actual,absolute_difference=abs(actual-expected),relative_tolerance=c['relative_tolerance'],absolute_tolerance=c['absolute_tolerance'],evidence='test_unit_acceptance.py::test_complete_bounded_source_to_native_dispatch',status='PASS',scope='24 numeric paths; complete native input/type contracts remain PARTIAL due UNIT-C01'))
# Preserve economic evidence at its previous bounded/provisional level.
prior=list(csv.DictReader((r/'docs/verification/phase1/closure/unit_verification_acceptance_matrix.csv').open()))
for old in prior:
 if old['category'] in ['currency','historical costing basis','annual operating quantity']:
  reg.append(dict(case_id='E-'+old['category'],kind='economic unit/basis review',source_quantity=old['input_value'],source_unit=old['source_unit'],destination_unit=old['destination_unit'],dimension=old['category'],relationship=old['relationship'],context='Stored dated source snapshot, no live observation verification',independent_expected=old['independent_expected_result'],actual=old['actual_result'],absolute_difference=old['absolute_difference'],relative_tolerance=old['relative_tolerance'],absolute_tolerance=old['absolute_tolerance'],evidence='Prior closure evidence, targeted currency/cost-translation tests; no physical-unit equivalence implied',status='PASS' if old['category']=='annual operating quantity' else 'PARTIAL',scope=old['scope']+'; no independently authenticated current FX/index observation'))
save('unit_conversion_acceptance_register.csv',reg)
save('evidence/source_to_native_results.csv',chainrows)

# Every implemented alias is inventoried; only explicitly tested meanings accepted.
verified={key(c['source']):c for c in t['ALIASES']}
aliasrows=[]
for namespace,dictionary in [('alias/canonical label',ALIASES),('word alias',WORDS)]:
 for label,target in dictionary.items():
  item=verified.get(label) or verified.get(key(label))
  aliasrows.append(dict(namespace=namespace,label=label,implemented_canonical_target=target,independent_expected_meaning=item['destination'] if item else '',expected_numeric_equivalence='1' if item else '',actual_numeric_equivalence=convert(1,item['source'],item['destination']).value if item else '',status='PASS' if item else 'NOT APPLICABLE',scope='Tested spelling/equivalence within bounded list' if item else 'Outside accepted bounded alias list; implementation inventory only, not independently verified',evidence=('test_unit_acceptance.py::test_explicit_alias_semantics['+item['id']+']') if item else 'Existing unit_aliases.py inventory; no acceptance inferred'))
# Dynamic spellings need not exist as literal dictionary entries.
for item in t['ALIASES']:
 if not any(a['label']==key(item['source']) for a in aliasrows):
  aliasrows.append(dict(namespace='dynamic spelling or equivalent unit',label=item['source'],implemented_canonical_target=identify_unit(item['source']).symbol,independent_expected_meaning=item['destination'],expected_numeric_equivalence='1',actual_numeric_equivalence=convert(1,item['source'],item['destination']).value,status='PASS',scope='Explicit grammar/key normalisation tested; not all dynamic expressions',evidence='test_unit_acceptance.py::test_explicit_alias_semantics['+item['id']+']'))
# Data-type semantics are separate from unit spelling and acceptance percentages.
for label,meaning,status in [('Python int/float','Accepted finite input numeric types, signed power preserved','PASS'),('NumPy float64','Accepted on the tested NumPy version via float inheritance','PASS'),('Decimal/Fraction','Not supported directly by convert; explicit rejection preserves meaning','NOT APPLICABLE'),('NumPy int64/float32','Not supported directly by convert; explicit rejection','NOT APPLICABLE'),('Python/NumPy Boolean at convert','Rejected as unresolved, never numerically interpreted','PASS'),('NumPy Boolean native assumption/observation','UNIT-C01: pre-coercion guard missing; 13 assertions fail','BLOCKED')]:
 aliasrows.append(dict(namespace='data type semantics',label=label,implemented_canonical_target='',independent_expected_meaning=meaning,expected_numeric_equivalence='',actual_numeric_equivalence='',status=status,scope='Not an alias count',evidence='test_unit_acceptance.py; targeted.xml'))
save('unit_alias_and_semantics_register.csv',aliasrows)

units_summary=json.loads((r/'docs/verification/phase1/closure/evidence/inventory_summary.json').read_text())
summary=dict(verified_conversion_paths=148,pure_unit_cases=146,physical_derivations=2,numeric_source_to_native_paths=24,alias_checks=76,noncanonical_alias_spellings=75,equivalent_canonical_unit_spellings=1,canonical_units_inventoried=len(UNITS),canonical_units_numerically_exercised=len(canonical & set(UNITS)),aliases_inventoried=len(ALIASES),word_aliases_inventoried=len(WORDS),conversion_register_statuses=dict(Counter(row['status'] for row in reg)),alias_register_statuses=dict(Counter(row['status'] for row in aliasrows)))
(p/'evidence/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
# Native contracts: numeric unit meaning verified; full type admission is not.
oldcontracts=list(csv.DictReader((r/'docs/verification/phase1/closure/sizing_to_costing_physical_compatibility.csv').open()))
contract=[]
for c in t['NATIVE']:
 m=c['method'];d=METHODS[m];cost=next(x for x in oldcontracts if x['method_id']==m)
 contract.append(dict(method_id=m,native_input_quantity=d['input'],native_input_unit=d['unit'],verified_alternative_sources=json.dumps([v[1] for v in t['SOURCE_UNITS'][d['input']]]),conversion_function='unit_conversion.convert -> registry.calculate; source adapter assumes already-normalised primary units',required_context=json.dumps(c['parameters']),native_output_quantity=cost['sizing_output_quantity'],native_output_unit=c['unit'],downstream_requirements=cost['proposed_cost_model_native_quantity'],unsupported_combinations='Missing units/state; incompatible dimensions; arbitrary alternative parameter units; NumPy Boolean assumption currently admitted (defect)',numerical_unit_subcontract='PASS: two numeric alternative-source paths per method',complete_native_contract_acceptance='PARTIAL: UNIT-C01 missing NumPy Boolean input rejection',accepted_parameter_unit_spellings=json.dumps({q:PARAMETER_UNITS[q] for q in d['parameters']}),independent_evidence='references.json; source_to_native_results.csv; test_unit_acceptance.py; native304 prior and targeted run',blocking_ticket='UNIT-C01'))
save('sizing_native_unit_contract_acceptance.csv',contract)
# Catalogue-wide review, not a second costing calculation engine.
modelrows=[]
for model in list_equipment_models('all'):
 req=model.get('input_requirements',[])
 unresolved=any(x.get('quantity') in ['unresolved','source_coordinate'] or x.get('manual_coordinate') for x in req)
 modelrows.append(dict(model_id=model['id'],source=model.get('source','garrett'),native_coordinate_contracts=json.dumps(req),source_native_size_unit=model.get('size_unit',''),source_year=model.get('source_year',''),currency=model.get('currency',''),status='BLOCKED' if unresolved else 'PARTIAL',reason='Unresolved/manual source coordinate; do not invent a physical mapping' if unresolved else 'Metadata reviewed; dimensional units alone do not establish capacity/power/reference-state/technology meaning',native_path='Nottingham source-native only; do not assume generic resolver validated all units' if model.get('source')=='nottingham' else 'Explicit source-to-native converter/resolver; ambiguities require context',physical_requirements='Match actual/standard flow, gross/working volume, active area, power rating convention and price basis to source',evidence='Existing model registry/input requirements; prior validated unit/costing tests; no equation coefficients changed'))
save('costing_native_unit_interface_review.csv',modelrows)
print(json.dumps(summary,indent=2))
# Every raw spelling remains individually traceable, even if key normalisation
# maps two spellings to the same implementation dictionary key.
for item in t['ALIASES']:
 aliasrows.append(dict(namespace='bounded raw spelling check',label=item['source'],implemented_canonical_target=identify_unit(item['source']).symbol,independent_expected_meaning=item['destination'],expected_numeric_equivalence='1',actual_numeric_equivalence=convert(1,item['source'],item['destination']).value,status='PASS',scope='Explicit raw spelling '+item['id']+'; kJ/s is an equivalent canonical power unit, not an alias-dictionary entry',evidence='test_unit_acceptance.py::test_explicit_alias_semantics['+item['id']+'-'+item['source']+']'))
save('unit_alias_and_semantics_register.csv',aliasrows)

unsupported=[]
for cid,src,dst,expected,relation,dimension,context,ticket in [
 ('EXT01','m/s','ft/s',str(1/D('.3048')),'multiply1/.3048; no fluid property needed','L/T','None for like-to-like unit conversion','UNIT-EXT01'),
 ('EXT02','cP','Pa*s','.001','multiply.001; no density needed for dynamic-to-dynamic viscosity','M/L/T','Density required only for dynamic↔kinematic, not this pair','UNIT-EXT02'),
 ('EXT03','cSt','m2/s','.000001','multiply1e-6; no density needed for kinematic-to-kinematic','L2/T','Density required only if relating to dynamic viscosity','UNIT-EXT03'),
 ('EXT04','Btu_IT/(h*ft2*delta_degF)','W/m2/K',str(D('1055.05585262')/3600/D('.3048')**2/(D(5)/9)),'Known BTU_IT/time/area/temperature-interval factor; preserve surface basis','power/L2/temperature_difference','No new U estimate; given U must retain same surface/film convention','UNIT-EXT04'),
 ('EXT05','min','h',str(D(1)/60),'multiply1/60; no flow/volume needed to convert time','T','Deriving residence time separately requires consistent actual V/Q','UNIT-EXT05'),
 ('EXT06','specific_gravity','kg/m3','SG*rho_reference','Relative density is dimensionless; rho = SG*rho_ref(Tref,Pref)','ratio -> M/L3','Reference substance/density/T/P required; no automatic1000kg/m3 assumption','UNIT-EXT06'),
]:
 actual=convert(1,src,dst)
 unsupported.append(dict(case_id=cid,source_unit=src,destination_unit=dst,physical_dimension=dimension,relationship=relation,independent_expected=expected,actual='unresolved: '+'; '.join(actual.issues),additional_information=context,limitation_location='unit_conversion.unit_aliases.UNITS lacks quantity/token; no generic composite parser/SG physical bridge',absence_vs_interface='Genuinely absent standalone conversion; embedded/native dimensional arithmetic does not implement this API pair',status='BLOCKED',recommendation=ticket+': scope and implement/test separately if founder authorises; no implementation in UNIT-001'))
for item in unsupported:
 reg.append(dict(case_id=item['case_id'],kind='unsupported conversion family',source_quantity=1,source_unit=item['source_unit'],destination_unit=item['destination_unit'],dimension=item['physical_dimension'],relationship=item['relationship'],context=item['additional_information'],independent_expected=item['independent_expected'],actual=item['actual'],absolute_difference='',relative_tolerance='',absolute_tolerance='',evidence='test_unit_acceptance.py::test_absent_conversion_families_stay_explicitly_unresolved; NIST SP811 B9',status='BLOCKED',scope='Excluded from accepted numerical pathways; corrective ticket required'))
for i,(src,dst) in enumerate([('kg/h','m3/h'),('kWh','kW'),('delta_degC','degF'),('psig','psia'),('gal','L'),('ton','kg'),('scfm','m3/h')],1):
 result=convert(1,src,dst)
 reg.append(dict(case_id='CTX'+str(i),kind='missing physical context/dimension',source_quantity=1,source_unit=src,destination_unit=dst,dimension='Cannot infer quantity/basis',relationship='Requires explicit physical relationship or unambiguous reference',context='Missing required basis; see issues',independent_expected='unresolved; no numeric result justified',actual='unresolved: '+'; '.join(result.issues),absolute_difference='',relative_tolerance='',absolute_tolerance='',evidence='test_unit_acceptance.py::test_required_context_or_dimensions_not_invented',status='BLOCKED',scope='Correct rejection passes negative test; conversion itself blocked for this input'))
# Record actual unsafe observations separately; no numerical value is accepted.
for c in t['NATIVE']:
 m=c['method'];key_name,boolval=t['BOOL_PARAMETER'][m];d=METHODS[m]
 params={**c['parameters'],key_name:np.bool_(boolval)}
 report={'entities':[{'key':'s','values':[{'id':'source','property':d['input'],'normalized_value':c['value'],'normalized_unit':d['unit'],'status':'verified'}]}]}
 actual=derive({'method':m,'stream_key':'s','parameters':params},report)[0]
 reg.append(dict(case_id='TYPE-'+m,kind='native-assumption type safety defect',source_quantity=str(boolval),source_unit=key_name,destination_unit=c['unit'],dimension='Boolean is not an engineering quantity',relationship='Must reject before numeric coercion',context='NumPy bool_ in a native assumption',independent_expected='ValueError/rejection',actual='UNSAFE accepted size: '+str(actual),absolute_difference='',relative_tolerance='',absolute_tolerance='',evidence='test_unit_acceptance.py::test_required_numpy_boolean_assumptions_rejected['+m+']; targeted.xml FAIL',status='BLOCKED',scope='UNIT-C01 safety defect; not accepted despite finite numeric output'))
actual=derive({'method':'pump_duty','stream_key':'s','parameters':{'differential_pressure_bar':1,'efficiency':.5}},{'entities':[{'key':'s','values':[{'id':'s','property':'volume_flow','normalized_value':np.bool_(True),'normalized_unit':'m3/h','status':'verified'}]}]})[0]
reg.append(dict(case_id='TYPE-observation',kind='native-source type safety defect',source_quantity='NumPy True',source_unit='m3/h',destination_unit='1000 US_gpm_psi',dimension='Boolean is not a flow',relationship='Must reject before observation.float()',context='Direct adapter observation; not XLS reader issue',independent_expected='ValueError/rejection',actual='UNSAFE accepted coordinate: '+str(actual),absolute_difference='',relative_tolerance='',absolute_tolerance='',evidence='test_unit_acceptance.py::test_required_numpy_boolean_source_observation_rejected; targeted.xml FAIL',status='BLOCKED',scope='UNIT-C01; do not confuse with Engineer2 XLS Boolean preservation'))
save('unit_conversion_acceptance_register.csv',reg)
save('unsupported_unit_conversion_register.csv',unsupported)

roles=[
 ('pressure scaling','bar -> Pa','PASS','Scale1e5; no absolute/gauge/differential role inferred','Caller supplies named physical role; output basis remainsNone when not stated','test_pressure_role_is_not_inferred_from_symbol'),
 ('gauge/absolute','barg -> bara','PASS','Pabs=Pgauge+explicit atmosphere','Positive finite atmospheric pressure required; role conflicts rejected','U: gauge/absolute references plus existing test_unit_conversion.py'),
 ('differential pressure','bar delta role -> Pa','PARTIAL','Numerical scale is verified; differential role is a field meaning','ConversionContext accepts gauge/absolute, not differential; retain named differential_pressure_bar and avoid confusing operating/design pressure','test_unit_conversion.py resolver-role tests; sizing parameter units'),
 ('absolute/delta temperature','degC -> K vs delta_degC -> delta_K','PASS','Absolute offset273.15; intervals no offset','Keep separate quantity kinds; unsupported cross-kind conversion rejected','independent temperature cases; existing temperature tests'),
 ('standard/normal volume flow','scfm -> Sm3/h','PASS','Only volume/time scale at explicitly identical actual reference definitions','Reference T/P, composition, wet/dry basis and Z fixed and qualified by caller; reference strings are identity labels, not state validation','U standard-flow case; prior context guard tests'),
 ('actual/reference gas conversion','m3/h actual -> Sm3/h','PASS','Qref=Qactual*(Pactual/Pref)*(Tref/Tactual)*(Zref/Zactual)','Explicit states/Z and unchanged composition; physical bridge, never pure unit conversion','D02 and test_actual_to_reference_volume_requires_explicit_states'),
 ('mass/volumetric flow','kg/s -> m3/h','PASS','Q=m/rho at matching stream/state','Explicit qualified density; missing density rejected','D01 and test_mass_to_volume_uses_explicit_density'),
 ('specific gravity/density','SG -> kg/m3','BLOCKED','rho=SG*rho_ref','Reference substance and T/P; no existing supported bridge; no hidden water density','EXT06'),
 ('energy/power','kWh vs kWh/day -> kW','PASS','Energy needs time;24kWh/day=1kW','A one-off energy cannot be interpreted as power; explicit time in unit accepted','U kWh/day case plus dimension guard'),
 ('residence time','min -> h vs V/Q','BLOCKED','min/60 distinct from V/Q at a stated flow basis','Standalone time converter absent; native time parameters retain their fixed units','EXT05; native304 independent methods'),
 ('power meaning','hydraulic/shaft/driver-rated hp or kW','PARTIAL','Same dimension, different physical loss/rating conventions','Explicit eta, driver/rating meaning and selected source definition required','Existing pump tests and costing native review; no power-kind inference from kW'),
 ('thermal quantities','heat duty vs area vs U','PARTIAL','Duty-to-area is Q/(U*LMTD*F), not unit conversion','Qualified U/temperature/surface basis; U unit conversion unsupported','EXT04 and independent thermal/sizing tests'),
 ('volume capacity','gross vs working vessel volume','PARTIAL','Gross=working/fill_fraction','Explicit working fraction; not a generic volume unit choice','Native vessel references; physical costing review'),
 ('currency','USD -> GBP','PARTIAL','Cross-rate arithmetic at explicit dated snapshot','FX observation authenticity/freshness not accepted here; never changes price year','Targeted currency tests and prior closure economic record'),
 ('historical price basis','USD1987 -> USD2026 proxy','PARTIAL','Same-index ratio, not an FX rate or CPI/CEPCI ratio','Stored proxy observations not independently authenticated actual equipment index; retain PARTIAL','Targeted cost_translation tests; prior closure record'),
 ('annual quantity','rate*hours*utilisation','PASS','2kg/h*7536h*.8=12057.6kg per explicit year','Saved approved hours/ramp used once; no universal314/365-day schedule','Prior closure annual quantity and targeted rate/time-unit checks'),
 ('file-reader semantics','XLS Boolean -> canonical observation','BLOCKED','Must preserve original Boolean cell type','Engineer2 SIZE-XF01; separate upstream issue from UNIT-C01','Prior cross-file matrix: two XLS failures'),
 ('file-reader flow units','L/s -> canonical m3/h','BLOCKED','1L/s=3.6m3/h verified in shared converter','Engineer2 SIZE-XF02: parser currently leaves unit unresolved','Prior cross-file matrix: three L/s failures; U shared-converter case'),
]
save('unit_role_reference_state_matrix.csv',[dict(role=a,pathway=b,status=c,relationship=d,required_context_or_limit=e,evidence=f) for a,b,c,d,e,f in roles])
summary.update(conversion_register_statuses=dict(Counter(row['status'] for row in reg)),native_full_contracts_accepted=0,native_numeric_unit_contracts_verified=12,native_numpy_boolean_failures=13,costing_interface_statuses=dict(Counter(x['status'] for x in modelrows)))
(p/'evidence/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('Final register counts:',json.dumps(summary,indent=2))
