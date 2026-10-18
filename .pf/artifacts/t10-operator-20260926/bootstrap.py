import ast,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
ASSIGN='t10-local-operator-completion-publish-bounded-authoritative-activity-sna'
RUN='garage-t10-local-operator-completion-publish-bounded-authoritative-activ'
CAP_SHA='bfb530a60eecc1632d3e5edc274e8a68c4c5547b34df8362773640d80fca37d7'
assert hashlib.sha256((ROOT/'.pf/contexts/assignment-capsules'/(ASSIGN+'.capsule.yaml')).read_bytes()).hexdigest()==CAP_SHA
source=(ROOT/'.pf/artifacts/t10-installed-delivery-20260926/work.py').read_text(encoding='utf-8')
source=source.replace('garage-t10-delivery-qualify-and-install-the-accepted-terminal-monitor-th',RUN).replace('t10-delivery-qualify-and-install-the-accepted-terminal-monitor-through-t',ASSIGN).replace('e7792b615d3531be0a677e431ef155000c84426a8291f118f25b0fe224aa5464',CAP_SHA).replace('t10-installed-delivery-20260926.md','t10-operator-20260926.md')
(HERE/'work.py').write_text(source,encoding='utf-8')
scope=['src/processforge_core/runtime_metrics.py','src/processforge_core/diagnostics.py','tools/pf_runtime/service.py','tools/pf_runtime/monitor.py','tools/processforge.py','bin/pf-server','bin/pf-server.bat','bin/pf-server.py','schemas/runtime-metrics.schema.json','tools/smoke_runtime_metrics.py','tools/smoke_server_operator.py','tools/smoke_diagnostics_configure.py','tools/smoke_runtime_monitor.py','docs/concepts/runtime-monitor.md','docs/ru/concepts/runtime-monitor.md','docs/concepts/diagnostics.md','docs/ru/concepts/diagnostics.md','docs/concepts/runtime-mcp.md','docs/ru/concepts/runtime-mcp.md','checksums/processforge.sha256']
spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/validate-process-forge-checksums.py');inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
baseline={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inv.public_files(ROOT)+[ROOT/'checksums/processforge.sha256']}
assert not (HERE/'baseline.json').exists()
for name in scope:
    p=ROOT/name
    if p.is_file():
        dest=HERE/'originals'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
tree=ast.parse((ROOT/'tools/processforge.py').read_text(encoding='utf-8-sig'))
journal_ast=ast.dump(next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='append_process_event'))
(HERE/'baseline.json').write_text(json.dumps({'scope':scope,'public_sha256':baseline,'protected_journal_function_ast':journal_ast},indent=2)+'\n',encoding='utf-8')
print('baseline public files',len(baseline),'declared scope',len(scope))
