"""Prepare scoped journal-repair evidence; preserve existing Work identities."""
import hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
ASSIGN='repair-the-project-event-journal-with-preserved-original-evidence-serial'
RUN='garage-repair-the-project-event-journal-with-preserved-original-evidence'
CAP=ROOT/'.pf/contexts/assignment-capsules'/(ASSIGN+'.capsule.yaml')
assert hashlib.sha256(CAP.read_bytes()).hexdigest()=='5016f5e22111a856d5c48409cd2bbe8d683b0f0f0bf1bd9f0769f38027967f5b'
work=(ROOT/'.pf/artifacts/t10-installed-delivery-20260926/work.py').read_text(encoding='utf-8')
work=work.replace('garage-t10-delivery-qualify-and-install-the-accepted-terminal-monitor-th',RUN).replace('t10-delivery-qualify-and-install-the-accepted-terminal-monitor-through-t',ASSIGN).replace('e7792b615d3531be0a677e431ef155000c84426a8291f118f25b0fe224aa5464','5016f5e22111a856d5c48409cd2bbe8d683b0f0f0bf1bd9f0769f38027967f5b').replace('t10-installed-delivery-20260926.md','event-journal-repair-20260926.md')
(HERE/'work.py').write_text(work,encoding='utf-8')
spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/validate-process-forge-checksums.py')
inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
paths=inv.public_files(ROOT)+[ROOT/'checksums/processforge.sha256']
baseline={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
assert not (HERE/'baseline.json').exists()
(HERE/'baseline.json').write_text(json.dumps(baseline,indent=2)+'\n',encoding='utf-8')
for name in ['tools/processforge.py','docs/concepts/session-telemetry.md','docs/ru/concepts/session-telemetry.md','checksums/processforge.sha256']:
    p=ROOT/name
    if p.exists():
        dest=HERE/'originals'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
print('baseline files',len(baseline))
