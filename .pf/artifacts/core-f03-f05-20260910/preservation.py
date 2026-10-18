from pathlib import Path
import hashlib,json
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
baseline=json.loads((BASE/'baseline.json').read_text(encoding='utf-8'))
allowed={'src/processforge_core/process_execution.py','tools/processforge.py','checksums/processforge.sha256'}
changed=[]
for name,expected in baseline['files'].items():
    path=ROOT/name
    actual=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    if actual!=expected and name not in allowed:changed.append(name)
inventory_changed=[]
for line in (BASE/'pre-integration-public.sha256').read_text(encoding='utf-8').splitlines():
    digest,name=line.split('  ',1)
    if name in allowed:continue
    path=ROOT/name
    if name=='AGENTS.md' and not path.exists():path=ROOT/'.pf/AGENTS.md'
    data=path.read_bytes() if path.is_file() else b''
    if b'\0' not in data:data=data.replace(b'\r\n',b'\n')
    if hashlib.sha256(data).hexdigest()!=digest:inventory_changed.append(name)
old_cli_digest=next(line.split('  ',1)[0] for line in (BASE/'pre-integration-public.sha256').read_text().splitlines() if line.endswith('  tools/processforge.py'))
cli=(ROOT/'tools/processforge.py').read_bytes().replace(b'\r\n',b'\n')
restored_cli=b''.join(line for line in cli.splitlines(keepends=True) if b'ReleaseCommand("smoke_work_evidence_freshness"' not in line and b'ReleaseCommand("smoke_work_completion_recovery"' not in line)
cli_preserved=hashlib.sha256(restored_cli).hexdigest()==old_cli_digest
result={'status':'PASS' if not changed and not inventory_changed and cli_preserved else 'FAIL','tracked_unrelated_changed':changed,'prior_public_inventory_changed':inventory_changed,'cli_only_two_registrations':cli_preserved,'allowed_existing_files':sorted(allowed)}
(BASE/'source-preservation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
raise SystemExit(0 if result['status']=='PASS' else 1)
