"""Synthetic native-wrapper bypass evidence; no real model or external network."""
import argparse,hashlib,importlib.util,json,os,platform,subprocess,sys,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from work import ROOT,HERE,save,state
assert state('feasibility-work-state')['stage']['id']=='investigation'
fixture=ROOT/'.pf/tmp/t07-engine-20260926/feasibility'
assert not fixture.exists();fixture.mkdir(parents=True)
workspace=fixture/'workspace';workspace.mkdir()
outside=fixture/'synthetic-home';outside.mkdir()
(outside/'config.txt').write_text('synthetic-home-canary',encoding='utf-8')
(outside/'plugin.py').write_text("VALUE = 'synthetic-plugin-canary'\n",encoding='utf-8')
received=[]
class Receiver(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        length=int(self.headers['Content-Length']);assert 0<=length<=4096
        received.append(self.rfile.read(length))
        self.send_response(200);self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'{}')
server=ThreadingHTTPServer(('127.0.0.1',0),Receiver)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
probe=fixture/'probe.py'
probe.write_text('''import importlib.util,json,os,subprocess,sys,urllib.request
from pathlib import Path
home=Path(os.environ['PF_SYNTHETIC_HOME'])
spec=importlib.util.spec_from_file_location('synthetic_plugin',home/'plugin.py')
plugin=importlib.util.module_from_spec(spec);spec.loader.exec_module(plugin)
result={'home_read':(home/'config.txt').read_text()=='synthetic-home-canary',
        'environment':os.environ.get('PF_SYNTHETIC_VALUE')=='synthetic-env-canary',
        'plugin':plugin.VALUE=='synthetic-plugin-canary',
        'child_process':subprocess.check_output([sys.executable,'-B','-c',"print('synthetic-child')"]).strip()==b'synthetic-child'}
request=urllib.request.Request(os.environ['PF_SYNTHETIC_ENDPOINT'],data=b'synthetic-network-canary',method='POST')
with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=3) as response:
    result['direct_loopback_network']=response.status==200
Path(os.environ['PF_SYNTHETIC_RESULT']).write_text(json.dumps(result))
''',encoding='utf-8')
manifest=fixture/'prepared-input.json'
document={'schema_version':1,'kind':'pf.prepared-input','identity':{'project_id':'synthetic','run_id':'synthetic-run','assignment_id':'synthetic-task','context_id':'synthetic-context','attempt':'1'},'project_root':str(workspace)}
raw=json.dumps(document).encode();manifest.write_bytes(raw)
digest='sha256:'+hashlib.sha256(raw).hexdigest()
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PF_PREPARED_INPUT_FILE':str(manifest),'PF_PREPARED_INPUT_SHA256':digest,'PF_WORKER_RUN_ID':'synthetic-run','PF_WORKER_TASK_ID':'synthetic-task','PF_WORKER_ATTEMPT':'1','PF_PROJECT_ROOT':str(workspace),'PF_SYNTHETIC_HOME':str(outside),'PF_SYNTHETIC_VALUE':'synthetic-env-canary','PF_SYNTHETIC_ENDPOINT':f'http://127.0.0.1:{server.server_port}/probe','PF_SYNTHETIC_RESULT':str(fixture/'result.json')}
cmd=[sys.executable,'-B',str(ROOT/'tools/prepared_executor.py'),'--prepared-input',str(manifest),'--prepared-sha256',digest,'--heartbeat',str(fixture/'heartbeat.json'),'--exit-path',str(fixture/'exit.json'),'--',sys.executable,'-B',str(probe)]
try:
    result=subprocess.run(cmd,cwd=workspace,env=env,capture_output=True,text=True,timeout=15)
    assert result.returncode==0,(result.stdout,result.stderr)
    observed=json.loads((fixture/'result.json').read_text())
    assert all(observed.values()) and received==[b'synthetic-network-canary']
finally:
    server.shutdown();server.server_close();thread.join(2)
save('native-feasibility.json',{'status':'PASS evidence of native bypass; strict capability unavailable','os':platform.platform(),'python':sys.version,'wrapper_sha256':hashlib.sha256((ROOT/'tools/prepared_executor.py').read_bytes()).hexdigest(),'argv':cmd,'exit_code':result.returncode,'observed':observed,'recipient':'synthetic numeric loopback only','fixture':str(fixture),'codex_cli':'not executed; separate qualification unavailable','managed_http_route':'candidate architecture, qualification pending implementation; no capability asserted'})
print(json.dumps(observed),flush=True)
