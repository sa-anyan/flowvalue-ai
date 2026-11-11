import os, subprocess, tempfile, json
from pathlib import Path
r=Path(__file__).resolve().parents[6];e=Path(__file__).parent
py=(r/'docs/audits/phase0/evidence/FV-G0-R01/python_location.txt').read_text().strip()
scratch=Path(tempfile.mkdtemp(prefix='flowvalue-unit002-'));guard=scratch/'guard';guard.mkdir()
(guard/'sitecustomize.py').write_text('import socket\ndef blocked(*a,**k): raise RuntimeError("External network disabled for verification")\nsocket.socket.connect=blocked\nsocket.create_connection=blocked\n')
env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ['KEY','TOKEN','SECRET','PASSWORD','DATABASE','FLOWVALUE','OPENAI','SUPABASE','PYTHONPATH'])}
env.update(AI_ENABLED='false',FLOWVALUE_CLOUD='false',FLOWVALUE_ASSESSMENT_DB=str(scratch/'test.sqlite'),PYTHONPATH=str(guard)+os.pathsep+str(r))
files=['docs/verification/phase1/units/catalogue_audit/evidence/test_catalogue_audit.py','backend/tests/test_native_boolean_safety.py','backend/tests/test_unit_conversion.py','backend/tests/test_unit_conversion_bridges.py','backend/tests/test_gas_compression_bridge.py','backend/tests/test_compressor_numerical_stability.py','backend/tests/test_heat_duty_validation.py','backend/tests/test_pump_numerical_safety.py','backend/tests/test_sizing_independent_verification.py','backend/tests/test_monte_carlo_horizon.py','backend/tests/test_currency_conversion.py','backend/tests/test_cost_translation.py']
(e/'targeted_files.json').write_text(json.dumps(files,indent=2)+'\n')
p=subprocess.run([py,'-m','pytest','-q',*files,'--junitxml='+str(e/'targeted.xml')],cwd=r,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(e/'targeted.txt').write_text(p.stdout);print(p.stdout[-5000:]);print('EXIT',p.returncode)
raise SystemExit(p.returncode)
