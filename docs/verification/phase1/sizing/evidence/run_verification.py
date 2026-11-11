import os,subprocess,tempfile,json
from pathlib import Path
r=Path(__file__).resolve().parents[5];e=r/'docs/verification/phase1/sizing/evidence'
py=Path((r/'docs/audits/phase0/evidence/FV-G0-R01/python_location.txt').read_text().strip())
scratch=Path((e/'scratch_location.txt').read_text().strip()); guard=scratch/'guard';guard.mkdir(exist_ok=True)
(guard/'sitecustomize.py').write_text('import socket\ndef blocked(*a,**k): raise RuntimeError("External network disabled for verification")\nsocket.socket.connect=blocked\nsocket.create_connection=blocked\n')
env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ['KEY','TOKEN','SECRET','PASSWORD','DATABASE','FLOWVALUE','OPENAI','SUPABASE','PYTHONPATH'])}
env.update(AI_ENABLED='false',FLOWVALUE_CLOUD='false',FLOWVALUE_ASSESSMENT_DB=str(scratch/'test.sqlite'),PYTHONPATH=str(guard)+os.pathsep+str(r))
import sys
mode=sys.argv[1]
if mode=='baseline':
 files=['backend/tests/test_engineering_sizing.py','backend/tests/test_gas_compression_bridge.py','backend/tests/test_heat_exchanger_basis.py','backend/tests/test_drying_balance.py','backend/tests/test_unit_conversion_bridges.py','backend/tests/test_monte_carlo_horizon.py']
 files=[x for x in files if (r/x).exists()]
elif mode=='new': files=['backend/tests/test_sizing_independent_verification.py']
else:
 files=[x for x in subprocess.check_output(['git','ls-files','backend'],cwd=r,text=True).splitlines() if Path(x).name.startswith('test_') and x.endswith('.py')]
 files+=['backend/tests/test_phase0_version_protection.py','backend/tests/test_monte_carlo_horizon.py','backend/tests/test_sizing_independent_verification.py']
 files=list(dict.fromkeys(files))
(e/(mode+'_files.json')).write_text(json.dumps(files,indent=2)+'\n')
p=subprocess.run([str(py),'-m','pytest','-q',*files,'--junitxml='+str(e/(mode+'.xml'))],cwd=r,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(e/(mode+'.txt')).write_text(p.stdout);print(p.stdout[-16000:]);print('EXIT',p.returncode)
