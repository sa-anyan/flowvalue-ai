import os,subprocess,tempfile,json,sys
from pathlib import Path
r=Path(__file__).resolve().parents[6];e=Path(__file__).parent
py=(r/'docs/audits/phase0/evidence/FV-G0-R01/python_location.txt').read_text().strip()
s=Path(tempfile.mkdtemp(prefix='flowvalue-unit003-'));g=s/'guard';g.mkdir()
(g/'sitecustomize.py').write_text('import socket\ndef blocked(*a,**k): raise RuntimeError("Network disabled for unit verification")\nsocket.socket.connect=blocked\nsocket.create_connection=blocked\n')
env={k:v for k,v in os.environ.items() if not any(t in k.upper() for t in ['KEY','TOKEN','SECRET','PASSWORD','DATABASE','FLOWVALUE','OPENAI','SUPABASE','PYTHONPATH'])}
env.update(AI_ENABLED='false',FLOWVALUE_CLOUD='false',FLOWVALUE_ASSESSMENT_DB=str(s/'test.sqlite'),PYTHONPATH=str(g)+os.pathsep+str(r))
mode=sys.argv[1] if len(sys.argv)>1 else 'targeted'
files=['backend/tests/test_unit003_active_conversions.py']
if mode=='legacy':files=['backend/tests/test_unit_acceptance.py']
if mode=='handoff':files=['backend/tests/test_unit003_active_conversions.py','backend/tests/test_garrett_integration.py','backend/tests/test_total_equipment_cost.py','backend/equipment_costing/indexes/nottingham/test_smoke.py']
if mode=='targeted':files += ['backend/tests/test_unit_conversion.py','backend/tests/test_unit_conversion_bridges.py','backend/tests/test_gas_compression_bridge.py','backend/tests/test_heat_exchanger_basis.py','backend/tests/test_native_boolean_safety.py','backend/tests/test_compressor_numerical_stability.py','backend/tests/test_heat_duty_validation.py','backend/tests/test_pump_numerical_safety.py','backend/tests/test_sizing_independent_verification.py','backend/tests/test_monte_carlo_horizon.py','backend/tests/test_openpytea_catalogue.py','backend/tests/test_engineering_sizing.py','backend/tests/test_production_sizing_bridge.py']
assert all((r/f).exists() for f in files), 'Missing explicitly selected test file'
(e/(mode+'_files.json')).write_text(json.dumps(files,indent=2)+'\n')
selection=['-k','test_every_new_alias_has_explicit_semantics'] if mode=='aliases' else []
p=subprocess.run([py,'-m','pytest','-q',*files,*selection,'--junitxml='+str(e/(mode+'.xml'))],cwd=r,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(e/(mode+'.txt')).write_text(p.stdout);print(p.stdout[-10000:]);print('EXIT',p.returncode)
raise SystemExit(p.returncode)
