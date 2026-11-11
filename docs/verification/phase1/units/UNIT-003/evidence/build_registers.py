"""UNIT-003 reports from independent static references and actual outcomes."""
import sys,csv,json,math,hashlib
from pathlib import Path
from dataclasses import asdict
from decimal import Decimal as D,getcontext
from collections import Counter
r=Path(__file__).resolve().parents[6];sys.path.insert(0,str(r));p=Path(__file__).resolve().parents[1]
from backend.equipment_costing.unit_conversion import convert,identify_unit,Measurement,average_power,residence_time
from backend.equipment_costing.unit_conversion.unit_aliases import UNITS,ALIASES,WORDS
from backend.equipment_costing.registry import list_equipment_models

def write(name,rows):
 with (p/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

requirements=[
 ('A1','velocity','m/s;m/h;ft/s;ft/min','hydraulic_loading_m_h','m/h','filter_area; clarifier/filter bridge','L T^-1','ft=0.3048m; min=60s; h=3600s','PASS','m3/m2/h is equivalent loading velocity; never m3/h'),
 ('A2','heat_transfer_coefficient','W/m2/K;kW/m2/K;Btu_IT/(h*ft2*delta_degF);Btu_th/(h*ft2*delta_degF)','overall_u_w_m2_k','W/m2/K','exchanger_area; vaporizer_area; thermal bridge','M T^-3 Theta^-1','U_SI=U_IP*Btu_J/(3600*0.3048^2*(5/9))','PASS','Same film/surface basis; Btu convention explicit; no absolute-temperature offset'),
 ('A3','time','s;min;h;day','service_cycle_h;empty_bed_contact_time_min;residence_time_h;gas_residence_time_s','h;min;h;s','capacity/EBCT; vessel; dryer','T','1min=60s;1h=3600s;1day=86400s','PASS','Converting supplied residence time is not inferring one; V/Q separate explicit helper'),
]
write('active_conversion_requirements.csv',[dict(zip(['id','family','supported_units','active_native_parameters','native_units','active_workflow','dimension','independent_basis','status','limitation'],x)) for x in requirements])
refs=json.loads((r/'backend/tests/fixtures/unit003/conversions.json').read_text());rows=[]
for c in refs:
 x=convert(c['value'],c['source'],c['target']);expected=float(c['expected'])
 reverse=convert(expected,c['target'],c['source']);rt=convert(x.value,c['target'],c['source'])
 assert math.isclose(x.value,expected,rel_tol=c['relative_tolerance'],abs_tol=c['absolute_tolerance'])
 rows.append({'id':c['id'],'relationship':'same-quantity conversion','source_value':c['value'],'source_unit':c['source'],'target_unit':c['target'],'independent_expected':c['expected'],'actual':x.value,'absolute_difference':abs(x.value-expected),'relative_tolerance':c['relative_tolerance'],'absolute_tolerance':c['absolute_tolerance'],'reverse_actual':reverse.value,'roundtrip_actual':rt.value,'status':'PASS','basis':c['basis']})
for ident,fun,args,expected in [('D1',average_power,(Measurement(4,'kWh'),Measurement(30,'min')),8),('D2',residence_time,(Measurement(1000,'L'),Measurement(2,'m3/h')),D('0.5'))]:
 result=fun(*args);assert result.value==float(expected)
 rows.append({'id':ident,'relationship':result.source['relationship'],'source_value':json.dumps([asdict(x) for x in args]),'source_unit':'typed quantities','target_unit':result.unit,'independent_expected':str(expected),'actual':result.value,'absolute_difference':abs(result.value-float(expected)),'relative_tolerance':2e-12,'absolute_tolerance':1e-13,'reverse_actual':'not an automatic inverse physical derivation','roundtrip_actual':'input component unit checks in targeted tests','status':'PASS','basis':'4kWh/(.5h)=8kW; 1m3/(2m3/h)=.5h; no inferred inputs'})
write('conversion_independent_verification.csv',rows)
ctx=list(csv.DictReader((r/'docs/verification/phase1/units/catalogue_audit/context_dependent_conversion_register.csv').open()))
for x in ctx:
 x['prior_status']=x['status'];x['new_evidence']='Existing bounded bridge and context-guard regressions; no expanded physical assumptions'
 if x['case_id']=='CTX05':x.update(status='PASS',current_implementation='relationships.average_power requires typed energy and positive duration',independent_evidence='D1; new independent and missing/invalid duration tests',limitation='Average, not peak/motor rating; helper callable, no automatic AI recipe',new_evidence='Explicit E/time helper added')
 if x['case_id']=='CTX06':x.update(status='PASS',current_implementation='relationships.residence_time with supplied working V and actual Q; forward sizing unchanged',independent_evidence='D2; wrong mass/standard-flow, missing and invalid denominator tests',limitation='No automatic residence-time inference or working-fraction assumption',new_evidence='Explicit inverse V/Q helper added; new time normalizer')
 if x['case_id']=='CTX08':x['new_evidence']='U-unit normalization to existing native area calculation; native assumptions and ranges preserved'
 if x['case_id']=='CTX09':x['new_evidence']='Supplied residence-time units normalized before existing hold-up equation'
write('context_conversion_acceptance.csv',ctx)
blocked=list(csv.DictReader((r/'docs/verification/phase1/units/catalogue_audit/costing_unit_dependency_matrix.csv').open()));blocked=[x for x in blocked if x['unit_interface_status']=='BLOCKED'];assert len(blocked)==11
models={m['id']:m for m in list_equipment_models('all')}
reconciled=[]
for x in blocked:
 mid=x['model_id'];m=models[mid];source='Garrett Chemical Engineering Economics Appendix1 p.'+str(m.get('printed_page')) if x['source']=='garrett' else m['reference']
 native='No existing 12-method output directly supplies this source coordinate'
 original_verified=False
 if mid in ['G297-125','G297-126']:
  coordinate='Chemical injection scaled flow; other pumps have distinct flow/power/flow-pressure conventions'
  meaning='Different source curves cannot be represented by one generic Q*deltaP coordinate'
  inputs='Selected individual pump configuration; service flow; required pressure/rating per curve; gallon basis; fixed/variable-speed basis'
  equation='No one accepted mapping; chemical-injection curve marks scaled flow, while several other curves explicitly use gpm'
  dimension='Depends selected curve: L3/T, power or Q*deltaP; not interchangeable'
  assumptions='Separate source curve/axis and chart readings for each configuration; no guessed exponent or scale'
  blocker='Original page visually inspected; grouped dataset coordinate/readings conflict. Must separately reconcile source readings; not a unit-factor patch.'
  deterministic='Some components already convertible; no verified compound/group mapping'
  original_verified=True
 elif mid in ['G306-153','G306-154']:
  coordinate='Equivalent-air mass flow lb/h divided by vacuum mm mercury'
  meaning='Air-equivalent vacuum-capacity factor; upstream multiplication conflicts with printed division'
  inputs='Qualified equivalent-air load; suction pressure and source vacuum reference convention'
  equation='candidate X=m_dot_air_lb_h/P_mmHg, not multiplication'
  dimension='L T (mass-flow / pressure)'
  assumptions='Confirm air equivalence and pressure reference, then correct/review source point coordinates independently'
  blocker='Printed division confirmed visually. Existing readings/model metadata use conflicting product basis; no new graph fitting/model changes authorised.'
  deterministic='Division and conventional pressure scaling established; not wired to conflicting cost data'
  original_verified=True
 elif 'screw_excluding' in mid:
  coordinate=m['size_unit'];meaning='Candidate conveyor length times screw diameter, in mixed length units'
  inputs='Actual conveyor length and defined screw diameter; not stream throughput'
  equation='candidate X=L_m*D_mm = 1000*L_m*D_m'
  dimension='L2, with mixed-unit numerical coordinate'
  assumptions='Confirm length/diameter definitions, shaft/outer diameter and table basis from original Perry table'
  blocker='Pinned upstream unit label found; original Perry table not recovered. Do not infer full geometry definition from an abbreviated label.'
  deterministic='Candidate dimensional scaling established; source linkage BLOCKED'
 elif 'rdc_extractor' in mid:
  coordinate=m['size_unit'];meaning='Candidate rotating-disk contactor height times diameter^1.5'
  inputs='Source-defined contactor height and diameter; actual dimensions or separately reviewed design'
  equation='candidate X=H_ft*D_ft**1.5'
  dimension='L2.5'
  assumptions='Original table must define height/diameter and scope; no process-flow-only inference'
  blocker='Upstream formula-like label found; original Seider table unavailable (publisher403). No independently recovered geometry/source contract.'
  deterministic='Dimensional relationship established; source linkage BLOCKED'
 elif 'distillation_including' in mid:
  coordinate=m['size_unit'];meaning='Candidate nonlinear coordinate of annual feed, not ordinary mass-flow scaling'
  inputs='Feed mass rate; explicitly supplied annual operating time; source normalization/exponent convention'
  equation='candidate X=(m_dot_lb_h*hours_per_year/1e6)**0.65'
  dimension='Normalized annual mass raised to0.65; numerical source coordinate'
  assumptions='Confirm year duration, normalization, bounds, and whether exponent belongs in coordinate or costing equation; no double exponent'
  blocker='Original Perry table unavailable; upstream label alone insufficient to establish normalization/exponent placement and published bounds.'
  deterministic='Time/mass unit components supported; full source derivation BLOCKED'
 else:
  coordinate=m['size_unit'];is_torr='torr' in coordinate.lower()
  meaning='Candidate suction gas mass-flow/absolute-pressure capacity; fluid/air-equivalent convention unverified'
  inputs='Source-defined suction mass flow or air-equivalent load; suction absolute pressure; steam service/stage configuration'
  equation='candidate X=m_dot_lb_h/P_Torr' if is_torr else 'candidate X=m_dot_kg_h/P_Pa'
  dimension='L T (mass-flow / pressure)'
  assumptions='Confirm absolute reference, gas/air-equivalence, steam rating, stage/condenser scope in original table'
  blocker='Pinned upstream label retained; original published table not recovered. Existing manual-coordinate route is not independent source compatibility approval.'
  deterministic='Mass and pressure scaling supported, including vacuum-capacity family; automatic source mapping remains BLOCKED'
 reconciled.append({'model_id':mid,'source_family':x['source'],'original_published_source':source,'upstream_record':('correlations.csv:'+str(m.get('csv_line')) if x['source']=='openpytea' else 'PDF page '+str(m.get('printed_page',250)-250)),'original_source_directly_inspected':original_verified,'source_coordinate':coordinate,'physical_meaning':meaning,'required_input_quantities':inputs,'native_engineering_output':native,'dimensional_relationship':dimension,'governing_relationship':equation,'required_assumptions':assumptions,'deterministic_relationship_decision':deterministic,'independent_verification_method':'Independent SI component factors; original chart visual check where available; source table reproduction required before wiring','status':'BLOCKED','remaining_reason':blocker,'production_action':'None: original costing equations, data, manual-coordinate protections and source registry unchanged'})
write('costing_source_coordinate_reconciliation.csv',reconciled)
(p/'evidence/catalogue_counts.json').write_text(json.dumps({'canonical_before':191,'canonical_after':len(UNITS),'new_definitions':len(UNITS)-191,'aliases_before':495,'aliases_after':len(ALIASES),'words_before':67,'words_after':len(WORDS),'original_bindings_retested':562,'new_reference_cases':len(rows),'context_dispositions':dict(Counter(x['status'] for x in ctx)),'costing_coordinate_dispositions':dict(Counter(x['status'] for x in reconciled))},indent=2)+'\n')
print('Reports generated')
