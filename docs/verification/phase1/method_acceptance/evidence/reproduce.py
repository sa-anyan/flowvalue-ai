"""Standalone review entry point: verify saved implementation version, then refs.

Run from repository root: python3 docs/verification/phase1/method_acceptance/evidence/reproduce.py
No reference values are generated with the implementation being reviewed.
"""
import hashlib,json,sys,math
from pathlib import Path
r=Path(__file__).resolve().parents[5];e=Path(__file__).parent;sys.path.insert(0,str(r))
manifest=json.loads((e/'implementation_manifest.json').read_text())
changed=[name for name,digest in manifest.items() if not (r/name).exists() or hashlib.sha256((r/name).read_bytes()).hexdigest()!=digest]
if changed:raise SystemExit('Recorded source version differs: '+', '.join(changed))
from backend.engineering_sizing.registry import calculate
from backend.orchestration.sizing import derive_size
from backend.equipment_costing.unit_conversion import convert,identify_unit
from backend.equipment_costing.unit_conversion.bridges import mechanical,production_sizing,liquid
native=json.loads((r/'backend/tests/fixtures/sizing_verification/references.json').read_text())
extra=json.loads((e/'additional_references.json').read_text())
def cv(value,unit,target=None):
 if value=='quantity':return identify_unit(unit).quantity
 c=convert(value,unit,target)
 if c.value is None:raise ValueError('; '.join(c.issues))
 return c.value
count=0
for c in native+extra:
 mid=c['method'];inputs=c.get('parameters',c.get('inputs'))
 if mid=='vessel_mass':result=mechanical.evaluate(inputs)
 elif mid=='vessel_productivity':result=production_sizing.vessel_productivity(inputs)
 elif mid=='mixing_power':result=liquid.evaluate(mid,c['value'],c['source_unit'],inputs,cv)
 elif mid in {'mass_residence','volume_residence'}:
  prop='mass_flow' if mid=='mass_residence' else 'volume_flow'
  report={'entities':[{'key':'s','values':[{'id':'legacy-ref','property':prop,'normalized_value':c['value'],'normalized_unit':c['source_unit'],'status':'verified'}]}]}
  result=derive_size({'sizing':{'method':mid,'stream_key':'s',**inputs}},report)
 else:result=calculate(mid,c['value'],inputs)
 rel=c.get('relative_tolerance',c.get('rtol'));ab=c.get('absolute_tolerance',c.get('atol'))
 assert result[1]==c['unit'] and math.isclose(result[0],float(c['expected']),rel_tol=rel,abs_tol=ab),(mid,result,c['expected'])
 print(c.get('id',mid),result[0],result[1],'PASS (bounded reference only)')
 count+=1
print(count,'independently specified reference cases reproduced; read applicability matrix before applying to a project.')
