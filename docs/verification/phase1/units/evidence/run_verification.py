import os,subprocess,tempfile,json
from pathlib import Path
r=Path(__file__).resolve().parents[5];e=r/'docs/verification/phase1/units/evidence'
py=Path((r/'docs/audits/phase0/evidence/FV-G0-R01/python_location.txt').read_text().strip())
scratch=Path(tempfile.mkdtemp(prefix='flowvalue-unit001-')); guard=scratch/'guard';guard.mkdir(exist_ok=True)
(guard/'sitecustomize.py').write_text('import socket\ndef blocked(*a,**k): raise RuntimeError("External network disabled for verification")\nsocket.socket.connect=blocked\nsocket.create_connection=blocked\n')
env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ['KEY','TOKEN','SECRET','PASSWORD','DATABASE','FLOWVALUE','OPENAI','SUPABASE','PYTHONPATH'])}
env.update(AI_ENABLED='false',FLOWVALUE_CLOUD='false',FLOWVALUE_ASSESSMENT_DB=str(scratch/'test.sqlite'),PYTHONPATH=str(guard)+os.pathsep+str(r))
import sys
mode=sys.argv[1]
if mode=='new':
 files=['backend/tests/test_unit_acceptance.py']
else:
 files=['backend/tests/test_unit_acceptance.py','backend/tests/test_unit_conversion.py','backend/tests/test_unit_conversion_bridges.py','backend/tests/test_gas_compression_bridge.py','backend/tests/test_heat_duty_validation.py','backend/tests/test_sizing_independent_verification.py','backend/tests/test_currency_conversion.py','backend/tests/test_cost_translation.py']
(e/(mode+'_files.json')).write_text(json.dumps(files,indent=2)+'\n')
p=subprocess.run([str(py),'-m','pytest','-q',*files,'--junitxml='+str(e/(mode+'.xml'))],cwd=r,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(e/(mode+'.txt')).write_text(p.stdout);print(p.stdout[-16000:]);print('EXIT',p.returncode)
