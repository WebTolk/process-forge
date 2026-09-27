"""Bounded reviewed test-stand delivery; preserve evidence and stop on any mismatch."""
from datetime import datetime, timezone
import hashlib, json, shutil, subprocess, sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
CANDIDATE=ROOT/'.pf/tmp/t06-installed-delivery-20260926/candidate'
CORE=Path('D:/.agents/processforge')
WP=Path('D:/.agents/processforge-workplace')
RUN='garage-t06-delivery-prerequisite-qualify-a-clean-isolated-candidate-cont'
T06='t06-pf-vision-alignment-r02-integrate-acceptance-for-work-resources-norm'
assert sys.argv[1:]==['--apply'], 'Explicit apply required'
assert not (HERE/'install-result.json').exists(), 'Never blindly repeat an attempted apply'
state=yaml.safe_load((ROOT/'.pf/runs'/RUN/'run.yaml').read_text(encoding='utf-8'))
result={'started_at':datetime.now(timezone.utc).isoformat(),'commands':[]}
build=json.loads((HERE/'candidate-corrected.json').read_text())
assert build.get('finished_at') and build['candidate_clean'] and build['payload_hashes_verified']==987
archive=Path(build['archive'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save():
    (HERE/'install-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
def run(label,argv,timeout=180):
    p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=timeout)
    row={'label':label,'time_utc':datetime.now(timezone.utc).isoformat(),'argv':list(map(str,argv)),
         'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    result['commands'].append(row);save();print(label,p.returncode,flush=True)
    assert p.returncode==0,p.stdout[-2000:]+p.stderr[-2000:]
    return p.stdout
def cli(base,*args):return [sys.executable,'-B',base/'bin/pf.py',*args]
assert sha(archive)==build['archive_sha256']
live=json.loads(run('delivery-state',cli(CANDIDATE,'work-state','--project-root',ROOT,'--workplace',WP,'--run',RUN,'--assignment','t06-delivery-prerequisite-qualify-a-clean-isolated-candidate-containing','--json')))
assert live['stage']['id']=='release-delivery' and live['run']['id']==RUN
plan=json.loads(run('final-update-plan',cli(CANDIDATE,'core-update','plan','--core-root',CORE,'--archive',archive,'--workplace-root',WP)))
assert not plan['blockers'] and plan['counts']=={'added':33,'changed':37,'locally_modified':0,'missing_owned':0,'removed':0,'restored':0,'unchanged':917}
assert plan['workplace_migration']['status']=='not_applicable' and not plan['workplace_migration']['operations']
status=json.loads(run('final-runtime-before',cli(CORE,'runtime','status','--workplace',WP,'--json')))
assert status['runtime']['running'] and status['status']=='ready' and status['active_workers']==0 and status['pending_runtime_jobs']==0
process=json.loads(run('runtime-command', ['powershell','-NoProfile','-Command',f"Get-CimInstance Win32_Process -Filter 'ProcessId = {int(status['pid'])}' | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"]))
assert 'runtime serve' in process['CommandLine'] and '--port 0 --interval 2.0' in process['CommandLine']
assert str(CORE/'tools/processforge.py').lower() in process['CommandLine'].lower()
result['runtime_settings']={'port':0,'interval':2.0,'prior_instance':status['instance_id'],'prior_pid':status['pid']}
protected=[WP/'workplace.yaml',WP/'terms.yaml',ROOT/'.codex/hooks.json',Path('C:/Users/musst/.codex/config.toml'),ROOT/'.pf/contexts/project-context.snapshot.yaml',ROOT/'.pf/contexts/assignment-capsules'/(T06+'.capsule.yaml')]
for rel in ['registries','runtime-drivers','mcp','tools','specializations','platform-contracts']:
    protected.extend(p for p in (WP/rel).rglob('*') if p.is_file() and p.suffix in {'.yaml','.yml','.json','.toml','.md'})
result['protected_sha256']={str(p):sha(p) for p in protected if p.is_file()}
prior=json.loads((ROOT/'.pf/artifacts/t06-integrated-acceptance-20260926/baseline.json').read_text())
assert all(sha(ROOT/p)==h for p,h in prior['frozen_sha256'].items())
result['frozen_before_verified']=len(prior['frozen_sha256'])
backup=HERE/'pre-install';backup.mkdir()
shutil.copy2(CORE/'processforge-core.manifest.json',backup/'old-manifest.json')
shutil.copy2(CORE/'runtime/core-update/last-apply.json',backup/'previous-last-apply.json')
shutil.copy2(WP/'runtime/pf-runtime/service.json',backup/'runtime-service.json')
for p in (WP/'runtime/pf-runtime/logs').glob('*.log'):
    shutil.copy2(p,backup/p.name)
old=json.loads((backup/'old-manifest.json').read_text())
assert all(sha(CORE/x['relative_path'])==x['sha256'] for x in old['files'])
result['old_payload_hashes_verified']=len(old['files']);save()
run('runtime-stop',cli(CORE,'runtime','stop','--workplace',WP,'--timeout','10'))
stopped=json.loads(run('runtime-stopped-status',cli(CORE,'runtime','status','--workplace',WP,'--json')))
assert not stopped['runtime']['running']
applied=json.loads(run('core-update-apply',cli(CANDIDATE,'core-update','apply','--core-root',CORE,'--archive',archive,'--workplace-root',WP,'--confirm'),300))
assert applied['status']=='applied'
result['backup_dir']=applied['backup_dir'];save()
manifest=json.loads((CORE/'processforge-core.manifest.json').read_text())
assert manifest==json.loads((ROOT/'.pf/tmp/t06-installed-delivery-20260926/extracted-corrected/processforge-core.manifest.json').read_text())
assert len(manifest['files'])==987
assert all(sha(CORE/x['relative_path'])==x['sha256'] for x in manifest['files'])
result['installed_payload_hashes_verified']=len(manifest['files'])
old_entries={x['relative_path']:x for x in old['files']}
update_backup=Path(applied['backup_dir'])
assert update_backup.resolve().is_relative_to((CORE/'runtime/core-update/backups').resolve())
assert json.loads((update_backup/'control/old-manifest.json').read_text())==old
assert json.loads((update_backup/'control/new-manifest.json').read_text())==manifest
assert set(applied['backed_up'])==set(plan['changed'])
assert all(sha(update_backup/rel)==old_entries[name]['sha256'] for name,rel in applied['backed_up'].items())
result['backup_hashes_verified']=len(applied['backed_up'])
assert not (CORE/'runtime/core-update/in-progress.json').exists()
assert json.loads((CORE/'runtime/core-update/last-apply.json').read_text())['status']=='applied'
assert all(sha(Path(p))==h for p,h in result['protected_sha256'].items())
result['protected_unchanged_before_start']=True;save()
run('runtime-start',cli(CORE,'runtime','start','--workplace',WP,'--port','0','--interval','2.0','--timeout','30','--json'))
after=json.loads(run('runtime-after-status',cli(CORE,'runtime','status','--workplace',WP,'--json')))
assert after['runtime']['running'] and after['status']=='ready' and after['instance_id']!=status['instance_id']
run('runtime-after-doctor',cli(CORE,'runtime','doctor','--workplace',WP))
run('workplace-after-doctor',cli(CORE,'doctor-workplace','--workplace',WP))
run('core-update-after-status',cli(CORE,'core-update','status','--core-root',CORE))
run('project-context-after',cli(CORE,'project-context-check','--project-root',ROOT,'--workplace',WP))
assert all(sha(Path(p))==h for p,h in result['protected_sha256'].items())
assert all(sha(ROOT/p)==h for p,h in prior['frozen_sha256'].items())
assert all(sha(ROOT/p)==h for p,h in build['source_raw_sha256'].items())
result['protected_unchanged_after_start']=True
result['frozen_after_verified']=len(prior['frozen_sha256'])
result['source_payload_unchanged']=True
result['finished_at']=datetime.now(timezone.utc).isoformat();save()
print(json.dumps({k:result[k] for k in ['backup_dir','installed_payload_hashes_verified','backup_hashes_verified','protected_unchanged_after_start','frozen_after_verified']}),flush=True)
