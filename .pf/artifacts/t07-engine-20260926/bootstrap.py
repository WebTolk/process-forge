import fnmatch,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
RUN='garage-implement-the-t07-provider-neutral-egress-engine-qualify-a-bounde'
ASSIGN='implement-the-t07-provider-neutral-egress-engine-qualify-a-bounded-enfor'
CAP_SHA='000b31cf7f3af61f3b7d07943712ae201e030b7c97afb681ea85313f6792cd37'
assert hashlib.sha256((ROOT/'.pf/contexts/assignment-capsules'/(ASSIGN+'.capsule.yaml')).read_bytes()).hexdigest()==CAP_SHA
prior=ROOT/'.pf/artifacts/t10-operator-runtime-fix-20260926'
s=(prior/'work.py').read_text(encoding='utf-8')
s=s.replace('garage-t10-local-operator-completion-publish-bounded-authoritative-activ',RUN).replace('t10-local-operator-completion-publish-bounded-authoritative-activity-sna',ASSIGN).replace('bfb530a60eecc1632d3e5edc274e8a68c4c5547b34df8362773640d80fca37d7',CAP_SHA).replace('t10-operator-20260926.md','t07-engine-20260926.md')
(HERE/'work.py').write_text(s,encoding='utf-8')
scope=['src/processforge_core/egress/**','src/processforge_core/work_context.py','src/processforge_core/prepared_input.py','src/processforge_core/prepared_resources.py','src/processforge_core/work_resources.py','src/processforge_core/process_execution.py','src/processforge_core/garage.py','tools/processforge.py','tools/prepared_executor.py','tools/codex_exec_worker.py','tools/pf_runtime/provider_adapters.py','tools/pf_runtime/builtin_provider_adapters.py','tools/pf_runtime/mcp_server.py','schemas/*egress*.json','schemas/execution-contract.schema.json','schemas/execution-context-package.schema.json','schemas/context-capsule.schema.json','schemas/assignment.schema.json','schemas/assignment-front-matter.schema.json','tools/smoke_egress*.py','tools/smoke_work_context*.py','tools/smoke_prepared*.py','docs/concepts/egress*.md','docs/ru/concepts/egress*.md','docs/concepts/work-context.md','docs/ru/concepts/work-context.md','docs/concepts/prepared-input.md','docs/ru/concepts/prepared-input.md','checksums/processforge.sha256']
spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/validate-process-forge-checksums.py');inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
files={p.relative_to(ROOT).as_posix():p for p in inv.public_files(ROOT)+[ROOT/'checksums/processforge.sha256']}
assert not (HERE/'baseline.json').exists()
for n,p in files.items():
    if any(fnmatch.fnmatchcase(n,g) for g in scope):
        target=HERE/'originals'/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
(HERE/'baseline.json').write_text(json.dumps({'scope_patterns':scope,'public_sha256':{n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()},'installed_candidate':'347c6d9e9ec36044c77540bb601477173a68db41','installed_update':'core-update-20260926T191610Z'},indent=2)+'\n',encoding='utf-8')
print('T07 baseline and standard stage helper ready',len(files))
