import os,sys,subprocess,tempfile,json,platform
from pathlib import Path
r=Path(__file__).resolve().parents[6];e=Path(__file__).parent
s=Path(tempfile.mkdtemp(prefix='fv-trace01-'));guard=s/'guard';guard.mkdir()
(guard/'sitecustomize.py').write_text('import socket\ndef blocked(*a,**k): raise RuntimeError("Network disabled for TRACE01 verification")\nsocket.socket.connect=blocked\nsocket.create_connection=blocked\n')
env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ['KEY','TOKEN','SECRET','PASSWORD','DATABASE','FLOWVALUE','OPENAI','SUPABASE','PYTHONPATH'])}
env.update(AI_ENABLED='false',FLOWVALUE_CLOUD='false',FLOWVALUE_ASSESSMENT_DB=str(s/'isolated.sqlite'),PYTHONPATH=str(guard)+os.pathsep+str(r))
files=['backend/tests/test_engineering_method_versions.py','backend/tests/test_method_acceptance.py','backend/tests/test_unit_conversion_bridges.py','backend/tests/test_heat_exchanger_basis.py','backend/tests/test_production_sizing_bridge.py','backend/tests/test_gas_compression_bridge.py']
(e/'focused_files.json').write_text(json.dumps(files,indent=2)+'\n')
(e/'runtime.json').write_text(json.dumps({'python':sys.executable,'version':platform.python_version(),'network':'blocked','AI':'disabled','assessment_storage':'isolated temporary'},indent=2)+'\n')
p=subprocess.run([sys.executable,'-m','pytest','-q',*files,'--junitxml='+str(e/'focused.xml')],cwd=r,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(e/'focused.txt').write_text(p.stdout);print(p.stdout[-6000:]);raise SystemExit(p.returncode)
