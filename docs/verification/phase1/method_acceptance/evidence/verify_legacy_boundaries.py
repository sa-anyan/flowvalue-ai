"""New shared-boundary counterexamples; never change Engineer-2 source here."""
import json,sys
from pathlib import Path
r=Path(__file__).resolve().parents[5];sys.path.insert(0,str(r))
from backend.orchestration.sizing import derive_size
rows=[]
for method,prop,unit,flow,params in [('volume_residence','volume_flow','m3/h',-10,{'residence_time_h':2,'working_fraction':.8}),('mass_residence','mass_flow','kg/h',-1000,{'density_kg_m3':800,'residence_time_h':2,'working_fraction':.8})]:
 report={'entities':[{'key':'s','values':[{'id':'METHOD-001-negative-flow','property':prop,'normalized_value':flow,'normalized_unit':unit,'status':'verified'}]}]}
 spec={'sizing':{'method':method,'stream_key':'s',**params}}
 try:
  result=derive_size(spec,report)
  row={'method':method,'expected':'reject negative sizing flow; no accepted negative vessel volume','actual':result,'result':'FAIL','owner':'Engineer2/shared legacy integration','inputs':spec,'source_report':report}
 except ValueError as exc:
  row={'method':method,'expected':'reject negative sizing flow','actual_rejection':str(exc),'result':'PASS'}
 rows.append(row)
p=Path(__file__).parent/'legacy_boundary_results.json';p.write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2));raise SystemExit(1 if any(x['result']=='FAIL' for x in rows) else 0)
