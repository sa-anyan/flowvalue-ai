import os,subprocess,tempfile,json,sys,platform
from pathlib import Path
r=Path(__file__).resolve().parents[5];e=Path(__file__).parent
recorded_python=(r/'docs/audits/phase0/evidence/FV-G0-R01/python_location.txt').read_text().strip()
py=recorded_python if Path(recorded_python).exists() else sys.executable
(e/'runtime.json').write_text(json.dumps({'recorded_prior_python':recorded_python,'prior_python_available':Path(recorded_python).exists(),'current_python':py,'python_version':platform.python_version()},indent=2)+'\n')
s=Path(tempfile.mkdtemp(prefix='flowvalue-method001-'));g=s/'guard';g.mkdir()
(g/'sitecustomize.py').write_text('import socket\ndef blocked(*a,**k): raise RuntimeError("External network disabled for engineering verification")\nsocket.socket.connect=blocked\nsocket.create_connection=blocked\n')
env={k:v for k,v in os.environ.items() if not any(t in k.upper() for t in ['KEY','TOKEN','SECRET','PASSWORD','DATABASE','FLOWVALUE','OPENAI','SUPABASE','PYTHONPATH'])}
env.update(AI_ENABLED='false',FLOWVALUE_CLOUD='false',FLOWVALUE_ASSESSMENT_DB=str(s/'test.sqlite'),PYTHONPATH=str(g)+os.pathsep+str(r))
files=['backend/tests/test_method_acceptance.py','backend/tests/test_compressor_numerical_stability.py','backend/tests/test_unit_conversion_bridges.py']
(e/'focused_files.json').write_text(json.dumps(files,indent=2)+'\n')
p=subprocess.run([py,'-m','pytest','-q',*files,'--junitxml='+str(e/'focused.xml')],cwd=r,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(e/'focused.txt').write_text(p.stdout);print(p.stdout[-2500:]);raise SystemExit(p.returncode)
