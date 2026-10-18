from datetime import datetime, timezone
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
result={'started_at':datetime.now(timezone.utc).isoformat(),'checks':[]}
paths=['tools/pf_runtime/provider_adapters.py','tools/pf_runtime/builtin_provider_adapters.py','tools/pf_runtime/codex_adapters.py','tools/pf_runtime/host.py','tools/pf_runtime/session_replay.py','src/processforge_core/host_integration.py','src/processforge_core/project_initialization.py','src/processforge_core/work_context.py','tools/processforge.py','tools/smoke_provider_adapter_admission.py','tools/smoke_conversation_completeness.py','tools/smoke_authenticated_report_content.py','tools/smoke_codex_exec_worker.py']
for name in paths:
    ast.parse((ROOT/name).read_text(encoding='utf-8-sig'),filename=name)
for name in ['docs/concepts/provider-adapters.md','docs/ru/concepts/provider-adapters.md','docs/concepts/work-execution-contract.md']:
    path=ROOT/name
    text=path.read_text(encoding='utf-8')
    assert all(line==line.rstrip() for line in text.splitlines()),name
    for link in re.findall(r'\]\(([^)]+)\)',text):
        if not link.startswith(('http:','https:','#')):
            assert (path.parent/link.split('#')[0]).exists(),(name,link)
    paths.append(name)
result['syntax_docs']='PASS'
for command in [['tools/smoke_provider_adapter_admission.py'],['tools/validate-process-forge-schemas.py'],['tools/validate-public-cleanliness.py'],['tools/validate-process-forge-checksums.py','--write'],['tools/validate-process-forge-checksums.py','--check']]:
    run=subprocess.run([sys.executable,'-B',*command],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=240)
    result['checks'].append({'command':command,'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
    print(command[0],run.returncode,flush=True)
    (HERE/'final-checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if run.returncode:
        raise SystemExit(run.returncode)
result['source_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths}
kernel=hashlib.sha256((ROOT/'tools/pf_runtime/raw_ingress_kernel.py').read_bytes()).hexdigest()
assert kernel=='7b3a99288d1e275eda98774f787a1b7b109c47c97bb55dcb2178298d11c5407a'
result['raw_kernel_unchanged']=kernel
capsule=ROOT/'.pf/contexts/assignment-capsules/t04-pf-vision-alignment-r02-implement-trusted-provider-adapters-and-prov.capsule.yaml'
result['main_legacy_capsule_sha256']=hashlib.sha256(capsule.read_bytes()).hexdigest()
assert result['main_legacy_capsule_sha256']=='d503b512dfa96ae942fd873f067405ffc8899cf36c29f06d4d09bc77a06add75'
result['finished_at']=datetime.now(timezone.utc).isoformat()
(HERE/'final-checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('PASS: source QA, unchanged raw kernel/main capsule and final hashes')
