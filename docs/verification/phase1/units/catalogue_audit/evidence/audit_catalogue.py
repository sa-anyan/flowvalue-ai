"""UNIT-002 verification only. Independent Decimal oracle; never a runtime adapter.
Run from repository root with PYTHONPATH=. and the verified Python environment.
"""
import csv, hashlib, json, math, re
from collections import Counter, defaultdict
from decimal import Decimal, getcontext
from pathlib import Path
getcontext().prec=45
ROOT=Path(__file__).resolve().parents[6]
OUT=Path(__file__).resolve().parents[1]
from backend.equipment_costing.unit_conversion.unit_aliases import UNITS, ALIASES, WORDS
from backend.equipment_costing.unit_conversion.unit_conversion import identify_unit, convert
from backend.equipment_costing.unit_conversion.models import ConversionContext
D=Decimal
inch=D('0.0254'); foot=D('0.3048'); pound=D('0.45359237'); gravity=D('9.80665')
us=231*inch**3; imp=D('0.00454609'); psi=pound*gravity/inch**2
# Btu_th reference is NIST's published 7-significant-digit factor, NOT the
# extra digits of production. Its half-last-place uncertainty is propagated.
btu=D('1055.05585262'); th=D('1054.350'); mmhg=D('133.322387415')
O={}
dims={'count':'1 (item semantic count)','tray_count':'1 (tray semantic count)','mass':'M','length':'L','area':'L^2','volume':'L^3','pressure':'M L^-1 T^-2','temperature':'Theta (absolute)','temperature_difference':'Theta (interval)','energy':'M L^2 T^-2','power':'M L^2 T^-3','boiler_power':'historical boiler-hp chart coordinate; thermal power basis unresolved','amount':'N','density':'M L^-3','mass_flow':'M T^-1','volume_flow':'L^3 T^-1','molar_flow':'N T^-1','standard_volume_flow':'L^3 T^-1 @ stated gas reference','flow_pressure_product':'M L^2 T^-3 (Q*deltaP coordinate)','vacuum_capacity':'L T (mass-flow/absolute-pressure coordinate)','flow_sqrt_head':'L^(7/2) T^-1'}
refs={'count':'item','tray_count':'tray','mass':'kg','length':'m','area':'m2','volume':'m3','pressure':'Pa','temperature':'K','temperature_difference':'delta_K','energy':'J','power':'W','boiler_power':'boiler_hp','amount':'mol','density':'kg/m3','mass_flow':'kg/s','volume_flow':'m3/s','molar_flow':'mol/s','standard_volume_flow':'Sm3/s','flow_pressure_product':'m3/s_Pa','vacuum_capacity':'kg/h/mmHg_abs','flow_sqrt_head':'m3/h_sqrt_m'}
def add(s,q,f=1,offset=0,basis=None,unc=0):
 O[s]={'quantity':q,'factor':D(f),'offset':D(offset),'pressure_basis':basis,'uncertainty':D(unc)}
for s,q in [('item','count'),('tray','tray_count')]:add(s,q)
for s,f in [('kg',1),('g','.001'),('mg','.000001'),('lb',pound),('oz',pound/16),('tonne',1000),('short_ton',2000*pound),('long_ton',2240*pound)]:add(s,'mass',f)
for s,f in [('m',1),('cm','.01'),('mm','.001'),('in',inch),('ft',foot)]:
 add(s,'length',f);add(s+'2','area',D(f)**2);add(s+'3','volume',D(f)**3)
for s,f in [('L','.001'),('mL','.000001'),('US_gal',us),('Imp_gal',imp)]:add(s,'volume',f)
for s,f in [('Pa',1),('kPa',1000),('MPa',1000000),('bar',100000),('mbar',100),('psi',psi),('atm',101325),('Torr',D(101325)/760),('mmHg',mmhg)]:add(s,'pressure',f)
for s,f,b in [('psig',psi,'gauge'),('psia',psi,'absolute'),('barg',100000,'gauge'),('bara',100000,'absolute'),('kPag',1000,'gauge'),('kPaa',1000,'absolute')]:add(s,'pressure',f,basis=b)
add('K','temperature');add('degC','temperature',offset='273.15');add('degF','temperature',D(5)/9,D('273.15')-32*D(5)/9);add('degR','temperature',D(5)/9)
for s,f in [('delta_K',1),('delta_degC',1),('delta_degF',D(5)/9)]:add(s,'temperature_difference',f)
for s,f in [('J',1),('kJ',1000),('MJ',1000000),('GJ',1000000000),('Btu_IT',btu),('Btu_th',th),('kWh',3600000)]:add(s,'energy',f,unc='.0005' if s=='Btu_th' else 0)
for s,f in [('W',1),('kW',1000),('MW',1000000),('mW','.001'),('hp',550*foot*pound*gravity),('metric_hp',75*gravity),('refrigeration_ton',12000*btu/3600)]:add(s,'power',f)
add('boiler_hp','boiler_power')
add('mol','amount');add('kmol','amount',1000)
for s,f in [('kg/m3',1),('g/cm3',1000),('lb/ft3',pound/foot**3)]:add(s,'density',f)
for s,v in list(O.items()):
 q={'mass':'mass_flow','volume':'volume_flow','energy':'power','amount':'molar_flow'}.get(v['quantity'])
 if q:
  for t,n in [('s',1),('min',60),('h',3600),('day',86400)]:add(s+'/'+t,q,v['factor']/n,unc=v['uncertainty']/n)
for s,f in [('cfm',foot**3/60),('US_gpm',us/60),('Imp_gpm',imp/60),('US_MGD',1000000*us/86400)]:add(s,'volume_flow',f)
for s,f in [('scfm',foot**3/60),('Nm3/h',D(1)/3600),('Sm3/h',D(1)/3600),('Sm3/s',1)]:add(s,'standard_volume_flow',f)
for s,f in [('US_gpm_psi',us/60*psi),('Imp_gpm_psi',imp/60*psi),('m3/s_Pa',1)]:add(s,'flow_pressure_product',f)
for s,f in [('kg/h/mmHg_abs',D(1)/3600/mmhg),('lb/h/mmHg_abs',pound/3600/mmhg)]:add(s,'vacuum_capacity',f)
for s,f in [('US_gpm_sqrt_ft',us/60*foot.sqrt()),('Imp_gpm_sqrt_ft',imp/60*foot.sqrt()),('m3/h_sqrt_m',D(1)/3600)]:add(s,'flow_sqrt_head',f)
assert set(O)==set(UNITS),(set(O)-set(UNITS),set(UNITS)-set(O))
# Independent alias grammar and manually enumerated English meanings.
W={}
for s,words in {
'item':'items|unit|units','tray':'trays','kg':'kilogram|kilograms','g':'gram|grams','mg':'milligram|milligrams','lb':'pound|pounds','oz':'ounce|ounces','tonne':'tonne|tonnes|metric ton|metric tons|metric tonnes','short_ton':'short ton|short tons|us ton|us tons','long_ton':'long ton|long tons|imperial ton','m':'metre|metres|meter|meters','cm':'centimeter|centimeters|centimetre|centimetres','mm':'millimeter|millimeters|millimetre|millimetres','in':'inch|inches','ft':'foot|feet','L':'litres|liters','mL':'millilitre|milliliter|millilitres|milliliters','US_gal':'us gallon|us gallons|u.s. gallons','Imp_gal':'imperial gallon|imperial gallons|uk gallon|uk gallons','K':'kelvin|kelvins','degC':'celsius|degrees celsius','degF':'fahrenheit|degrees fahrenheit','degR':'rankine','refrigeration_ton':'refrigeration ton|refrigeration tons|ton of refrigeration|tons of refrigeration','boiler_hp':'boiler horsepower'}.items():
 for w in words.split('|'):W[w]=s
S={'lbs':'lb','lbm':'lb','metric_ton':'tonne','metric tonne':'tonne','l':'L','litre':'L','liter':'L','ml':'mL','US gal':'US_gal','gal_US':'US_gal','Imperial gal':'Imp_gal','gal_Imp':'Imp_gal','°C':'degC','C':'degC','°F':'degF','F':'degF','°R':'degR','delta_C':'delta_degC','delta_°C':'delta_degC','delta_F':'delta_degF','delta_°F':'delta_degF','HP':'hp','US gal/min':'US_gpm','Imperial gal/min':'Imp_gpm','m3/s*Pa':'m3/s_Pa','ft_height':'ft','bar_gauge':'barg','bar_abs':'bara','bar_absolute':'bara','psi_gauge':'psig','psi_abs':'psia','psi_absolute':'psia','US MGD':'US_MGD','MGD_US':'US_MGD'}
def alias_oracle(a):
 if a in O:return a
 if a in S:return S[a]
 if a.startswith('sq ') and a[3:] in ['m','cm','mm','in','ft']:return a[3:]+'2'
 if a.startswith('cu ') and a[3:] in ['m','cm','mm','in','ft']:return a[3:]+'3'
 m=re.fullmatch(r'(.+)/(sec|second|seconds|minute|minutes|hr|hour|hours|d|days)',a)
 if m:
  t={'sec':'s','second':'s','seconds':'s','minute':'min','minutes':'min','hr':'h','hour':'h','hours':'h','d':'day','days':'day'}[m[2]]
  candidate=m[1]+'/'+t
  if candidate in O:return candidate
 raise AssertionError('No independent alias meaning: '+a)
def context(s):
 v=O[s]; kw={}
 if v['quantity']=='standard_volume_flow':kw.update(input_gas_reference='dry gas; 273.15 K; 101325 Pa absolute; Z=1; same composition',target_gas_reference='dry gas; 273.15 K; 101325 Pa absolute; Z=1; same composition')
 if v['pressure_basis']:kw.update(input_pressure_basis=v['pressure_basis'],target_pressure_basis=v['pressure_basis'])
 return ConversionContext(**kw)
def expected(s,t,x):
 a,b=O[s],O[t];return (D(str(x))*a['factor']+a['offset']-b['offset'])/b['factor']
def tol(s,t,x):return max(1e-13,abs(float(D(str(x))*O[s]['uncertainty']/O[t]['factor']))+abs(float(expected(s,t,x)))*2e-12)
RESULTS=[]
def check(name,ok,detail=''):
 RESULTS.append({'check':name,'passed':bool(ok),'detail':str(detail)})
def write(name,rows):
 assert rows,name
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
old=json.loads((ROOT/'backend/tests/fixtures/unit_acceptance/references.json').read_text())
prior=set()
for v in old:
 for k in ['source','destination']:prior.add(identify_unit(v[k],context=ConversionContext(**v['context'])).symbol)
prior &= set(O)
assert len(prior)==143
new=set(O)-prior;assert len(new)==48
(OUT/'evidence/independent_oracle.json').write_text(json.dumps(O,default=str,indent=2)+'\n')
(OUT/'evidence/new_unit_ids.json').write_text(json.dumps(sorted(new),indent=2)+'\n')
numeric=[]
for s,v in sorted(O.items()):
 d=UNITS[s];q=v['quantity'];t=refs[q]
 check(s+':definition',d.quantity==q and d.pressure_basis==v['pressure_basis'] and abs(d.factor-float(v['factor']))<=max(1e-14,float(v['uncertainty'])+abs(float(v['factor']))*2e-12) and math.isclose(d.offset,float(v['offset']),abs_tol=1e-12),repr(d))
 # Do not rerun prior 143 forward fixture paths: reuse existing immutable evidence.
 row={'canonical_id':s,'evidence_origin':'UNIT-001 reused 143-unit evidence' if s in prior else 'UNIT-002 new targeted check','reference_unit':t,'input':1,'independent_expected':str(expected(s,t,1)),'actual':'see historical evidence','absolute_tolerance':tol(s,t,1),'forward':'REUSED','reverse':'REUSED','round_trip':'REUSED','boundary':'REUSED','acceptance':'PASS','scope':'Published-factor precision; same declared state/quantity; not equipment design acceptance'}
 if s=='boiler_hp':
  row.update(acceptance='PARTIAL',scope='Recognition and identity only; no independently established source-specific thermal rating',forward='IDENTITY ONLY',reverse='IDENTITY ONLY',round_trip='IDENTITY ONLY',boundary='identity checks')
 if s in new:
  c=context(s);r=convert(1,s,t,context=c);e=float(expected(s,t,1));ok=r.status=='converted' and abs(r.value-e)<=tol(s,t,1);check(s+':forward',ok,r)
  back=convert(e,t,s,context=c);rt=convert(r.value,t,s,context=c) if ok else back
  reverse_ok=back.status=='converted' and abs(back.value-1)<=max(2e-12,tol(s,t,1)*float(O[t]['factor']/v['factor']))
  rt_ok=rt.status=='converted' and math.isclose(rt.value,1,rel_tol=2e-12,abs_tol=1e-13)
  check(s+':reverse',reverse_ok,back);check(s+':roundtrip',rt_ok,rt)
  boundary=True
  signed=q in ['temperature_difference','power','energy','mass_flow','volume_flow','molar_flow','standard_volume_flow']
  for x in [0,-1]:
   r0=convert(x,s,t,context=c);valid=x==0 or signed
   ok0=(r0.status=='converted' and abs(r0.value-float(expected(s,t,x)))<=tol(s,t,x)) if valid else r0.status=='unresolved'
   check(s+':boundary:'+str(x),ok0,r0);boundary &= ok0
  for x in [float('nan'),float('inf'),-float('inf'),True]:check(s+':invalid:'+repr(x),convert(x,s,t,context=c).status=='unresolved')
  check(s+':invalid_unit',convert(1,s,'nonsense_UNIT',context=c).status=='unresolved')
  row.update(actual=r.value,forward='PASS' if ok else 'FAIL',reverse='PASS' if reverse_ok else 'FAIL',round_trip='PASS' if rt_ok else 'FAIL',boundary='PASS' if boundary else 'FAIL')
 numeric.append(row)
write('canonical_unit_numerical_verification.csv',numeric)
alias_rows=[]
for namespace,items in [('ALIASES',ALIASES),('WORDS',WORDS)]:
 for a,declared in sorted(items.items()):
  wanted=alias_oracle(a) if namespace=='ALIASES' else W[a]
  result=identify_unit(a);recognition=result.symbol==wanted and declared==wanted and result.quantity==O[wanted]['quantity']
  check(namespace+':'+a,recognition,result)
  variants=['  '+a+'  ',a.replace(' ','   ')]
  if namespace=='WORDS':variants.append(a.upper())
  if '2' in a or '3' in a:variants.extend([a.replace('2','²').replace('3','³'),a.replace('2','^2').replace('3','^3')])
  if '°' in a:variants.append(a.replace('°','º'))
  for variant in variants:check(namespace+':spelling:'+variant,identify_unit(variant).symbol==wanted)
  # Numerical meaning independently anchored even for aliases of previously tested units.
  t=refs[O[wanted]['quantity']];r=convert(1,a,t,context=context(wanted));meaning=r.status=='converted' and abs(r.value-float(expected(wanted,t,1)))<=tol(wanted,t,1)
  check(namespace+':meaning:'+a,meaning,r)
  alias_rows.append({'namespace':namespace,'alias':a,'registry_target':declared,'independent_intended_target':wanted,'physical_quantity':O[wanted]['quantity'],'recognition':'PASS' if recognition else 'FAIL','numeric_meaning':'IDENTITY ONLY' if wanted=='boiler_hp' else ('PASS' if meaning else 'FAIL'),'variant_probes':json.dumps(variants),'status':'PARTIAL' if wanted=='boiler_hp' else 'PASS'})
write('unit_alias_verification.csv',alias_rows)
# Every semantic quantity pair. Independent category compatibility expectation;
# dimensions alone deliberately do not erase distinctions such as item vs tray.
matrix=[]
for qa,sa in refs.items():
 for qb,sb in refs.items():
  r=convert(1,sa,sb,context=context(sa));want=qa==qb
  check('dimension:'+qa+'->'+qb,(r.status=='converted')==want,r)
  matrix.append({'input_quantity':qa,'target_quantity':qb,'input_dimension':dims[qa],'target_dimension':dims[qb],'example_input':sa,'example_target':sb,'expected':'compatible within same declared context' if want else 'reject semantic/physical mismatch','actual':r.status,'status':'PASS' if (r.status=='converted')==want else 'FAIL'})
write('unit_dimensional_compatibility_matrix.csv',matrix)
for a in ['MW','mW']:check('case:'+a,identify_unit(a).symbol==a)
for a in ['Mw','mw','m₃','barₐ','MGD','ton','gal','Btu','gpm']:
 try:identify_unit(a);ok=False
 except ValueError:ok=True
 check('unsupported_or_ambiguous:'+a,ok)
# Context safeguards, not fabricated engineering inputs.
for a,b in [('kg/h','m3/h'),('J','W'),('cfm','scfm'),('degC','delta_degC'),('item','tray'),('boiler_hp','W')]:check('context:reject:'+a+'->'+b,convert(1,a,b).status=='unresolved')
check('context:gauge_requires_atmosphere',convert(1,'barg','bara').status=='unresolved')
r=convert(1,'barg','bara',context=ConversionContext(atmospheric_pressure_pa=101325));check('context:gauge_with_atmosphere',r.status=='converted' and math.isclose(r.value,2.01325,abs_tol=1e-12))
check('context:gas_requires_reference',convert(1,'scfm','Nm3/h').status=='unresolved')
check('context:gas_reference_mismatch',convert(1,'scfm','Nm3/h',context=ConversionContext(input_gas_reference='A',target_gas_reference='B')).status=='unresolved')
for a,b,x in [('K','degC',0),('degC','K',-273.15),('degF','K',-459.67)]:check('temperature:absolute_zero:'+a,convert(x,a,b).status=='converted')
for a,x in [('K',-1),('degC',-274),('degF',-460)]:check('temperature:below_zero:'+a,convert(x,a,'K').status=='unresolved')
# Current interface inventory regenerated via public requirement contracts, not
# trusting stale historical row counts alone.
from backend.equipment_costing.registry import list_equipment_models
models=list_equipment_models("all")
(OUT/'evidence/live_model_inventory_type.txt').write_text(repr(type(models))+'\n'+repr(models[:1])[:1500])
# Detailed source contract snapshot is reconciled separately by caller if API differs.
costs=list(csv.DictReader((ROOT/'docs/verification/phase1/units/costing_native_unit_interface_review.csv').open()))
assert len(costs)==594
assert len(models)==594 and {m["id"] for m in models}=={c["model_id"] for c in costs}
usage=defaultdict(set); dep=[]
for row in costs:
 live=next(m for m in models if m['id']==row['model_id'])
 contracts=live.get('input_requirements',[]);issues=[];coordinates=[]
 for c in contracts:
  unit=c.get('target_unit',c.get('unit'));poss=set();notes=[]
  if unit:
   try:poss.add(identify_unit(unit).symbol)
   except ValueError:
    for basis in ['US','Imperial']:
     for ton in ['metric','short','long','refrigeration']:
      try:poss.add(identify_unit(unit,context=ConversionContext(input_gallon_basis=basis,input_ton_basis=ton,btu_basis='IT')).symbol)
      except ValueError:pass
    if poss:notes.append('Explicit source basis required; alternatives are conditional, not approved selections')
  if c.get('issue') or not poss:
   if c.get('required',True):issues.append(c.get('name','size')+': '+str(c.get('issue') or 'unsupported unit '+str(unit)))
  for p in poss:
   # scaled aliases are derived definitions, retain base dependency.
   base=re.sub(r'^(1000|10|1e\+06) ', '',p)
   if base in O:usage[base].add(row['model_id'])
  coordinates.append({'coordinate':c.get('name','size'),'unit':unit,'quantity':c['quantity'],'conditional_canonical_units':sorted(poss),'required':c.get('required',True),'limitations':notes,'issue':c.get('issue')})
 dep.append({'model_id':row['model_id'],'source':row['source'],'native_contracts':json.dumps(coordinates),'unit_interface_status':'BLOCKED' if issues else 'PARTIAL','missing_required_coordinates':'; '.join(issues),'physical_meaning_requirements':row['physical_requirements'],'acceptance_scope':'Unit resolution only; source capacity/surface/power/state convention still requires engineering validation'})
write('costing_unit_dependency_matrix.csv',dep)
native=list(csv.DictReader((ROOT/'docs/verification/phase1/units/sizing_native_unit_contract_acceptance.csv').open()))
sizing=defaultdict(set)
for row in native:
 candidates=[row['native_input_unit'],row['native_output_unit']]
 for variants in json.loads(row['accepted_parameter_unit_spellings']).values():candidates+=variants
 for unit in candidates:
  try:sizing[identify_unit(unit).symbol].add(row['method_id'])
  except ValueError:pass
master=[]
for s,v in sorted(O.items()):
 alias=[a for a in alias_rows if a['independent_intended_target']==s]
 master.append({'canonical_identifier':s,'display_symbol':UNITS[s].symbol,'physical_quantity':v['quantity'],'dimensional_representation':dims[v['quantity']],'base_or_reference_unit':refs[v['quantity']],'production_multiplier':UNITS[s].factor,'independent_multiplier':str(v['factor']),'production_offset':UNITS[s].offset,'independent_offset':str(v['offset']),'pressure_basis':v['pressure_basis'],'aliases':json.dumps([a['alias'] for a in alias if a['namespace']=='ALIASES']),'word_aliases':json.dumps([a['alias'] for a in alias if a['namespace']=='WORDS']),'conversion_function':'backend.equipment_costing.unit_conversion.unit_conversion.convert','native_sizing_methods':'; '.join(sorted(sizing[s])),'costing_model_ids':'; '.join(sorted(usage[s])),'active_support':'recognised historical identity only' if s=='boiler_hp' else 'finite advertised catalogue; context guards apply','independent_numerical_verification':'identity only; thermal rating unresolved' if s=='boiler_hp' else ('UNIT-001 reused + UNIT-002 independent definition/alias audit' if s in prior else 'UNIT-002 new forward/reverse/roundtrip/boundary tests'),'context_dependent':v['quantity'] in ['pressure','standard_volume_flow','boiler_power'],'usage':'native contract/model unit' if sizing[s] or usage[s] else 'not a direct native target; advertised source-unit capability remains in scope','primary_status':'PARTIAL' if s=='boiler_hp' else 'PASS','limitation':'UNIT-002-C01 source-specific boiler-hp thermal basis' if s=='boiler_hp' else ('Btu_th checked at NIST published precision, not every stored digit' if 'Btu_th' in s else 'Physical/model semantic context not inferred from dimensional conversion')})
write('canonical_unit_master_register.csv',master)
# Exact equal-factor groups are often intentional alternate spellings, not defects.
groups=defaultdict(list)
for s,v in O.items():groups[(v['quantity'],str(v['factor']),str(v['offset']),v['pressure_basis'])].append(s)
(OUT/'evidence/equivalent_definition_groups.json').write_text(json.dumps([g for g in groups.values() if len(g)>1],indent=2)+'\n')
(OUT/'evidence/check_results.json').write_text(json.dumps(RESULTS,indent=2)+'\n')
summary={'canonical':len(O),'prior_units':len(prior),'new_units':len(new),'physical_numerically_verified':190,'primary_dispositions':dict(Counter(r['primary_status'] for r in master)),'aliases':len(ALIASES),'words':len(WORDS),'alias_statuses':{ns:dict(Counter(r['status'] for r in alias_rows if r['namespace']==ns)) for ns in ['ALIASES','WORDS']},'checks':len(RESULTS),'failed_checks':[r for r in RESULTS if not r['passed']],'costing_models':len(dep),'costing_status':dict(Counter(r['unit_interface_status'] for r in dep)),'source_counts':dict(Counter(r['source'] for r in dep)),'sizing_methods':len(native),'units_with_direct_sizing_usage':sum(bool(sizing[s]) for s in O),'units_with_direct_costing_usage':sum(bool(usage[s]) for s in O),'remaining_new_numeric_units':sorted(new)}
(OUT/'evidence/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
assert not summary['failed_checks'],'Audit found failed checks; inspect before accepting'
