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
paths=['src/processforge_core/prepared_input.py','src/processforge_core/prepared_resources.py',
       'tools/prepared_executor.py','tools/processforge.py','tools/codex_exec_worker.py',
       'tools/smoke_prepared_execution_context.py','tools/smoke_worker_workspace_access.py',
       'tools/smoke_codex_exec_worker.py','tools/smoke_codex_worker_governance.py']
for name in paths:
    ast.parse((ROOT/name).read_text(encoding='utf-8-sig'),filename=name)
for name in ['docs/concepts/prepared-input.md','docs/ru/concepts/prepared-input.md','docs/concepts/work-execution-contract.md']:
    path=ROOT/name
    body=path.read_text(encoding='utf-8')
    assert not body.startswith('\ufeff'),name
    assert all(line==line.rstrip() for line in body.splitlines()),name
    for link in re.findall(r'\]\(([^)]+)\)',body):
        if not link.startswith(('http:','https:','#')):
            assert (path.parent/link.split('#')[0]).exists(),(name,link)
    paths.append(name)
for name in ['schemas/prepared-input.schema.json','schemas/runtime-driver.schema.json',
             'templates/runtime-drivers/generic-shell.yaml','templates/worker-launch-prompt.md']:
    paths.append(name)
assert 'ReleaseCommand("smoke_prepared_execution_context"' in (ROOT/'tools/processforge.py').read_text(encoding='utf-8')
result['syntax_docs_registration']='PASS'
for command in [['tools/validate-process-forge-schemas.py'],['tools/validate-public-cleanliness.py'],
                ['tools/validate-process-forge-checksums.py','--write'],['tools/validate-process-forge-checksums.py','--check']]:
    run=subprocess.run([sys.executable,'-B',*command],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=240)
    result['checks'].append({'command':command,'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
    print(command[0],run.returncode,flush=True)
    (HERE/'final-checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if run.returncode:
        raise SystemExit(run.returncode)
result['source_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths}
capsule=ROOT/'.pf/contexts/assignment-capsules/t05-pf-vision-alignment-r02-prepare-bounded-authorized-immutable-executi.capsule.yaml'
result['main_legacy_capsule_sha256']=hashlib.sha256(capsule.read_bytes()).hexdigest()
assert result['main_legacy_capsule_sha256']=='9f4967fd988154fd1e499e7f3f3833e028138f3944b294f409736b56141eeecd'
result['finished_at']=datetime.now(timezone.utc).isoformat()
(HERE/'final-checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('PASS: source QA, registration, private boundaries and unchanged primary capsule hashes')
