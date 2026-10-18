"""Apply exactly once through installed PF core-update; preserve ownership evidence."""
import shutil
from activity import inspect_activity
from work import *

assert sys.argv[1:]==['--apply']
assert not (HERE/'install.json').exists(), 'Inspect status/repair before any retry'
assert state('install-work-state')['stage']['id']=='release-delivery'
build=json.loads((HERE/'build.json').read_text(encoding='utf-8'))
assert build.get('finished_at') and build['candidate_clean']
archive=Path(build['archive']);assert sha(archive)==build['archive_sha256']
plan=json.loads(command('final-update-plan',cli('core-update','plan','--core-root',CORE,'--archive',archive,'--workplace-root',WP)))
assert not plan['blockers'] and plan['counts']==build['plan_counts']
assert not plan['workplace_migration']['operations']
old=json.loads((CORE/'processforge-core.manifest.json').read_text(encoding='utf-8'))
assert old==build['old_manifest'] and all(sha(CORE/x['relative_path'])==x['sha256'] for x in old['files'])
activity=inspect_activity();save('activity-final.json',activity)
before=activity['service']
proc=json.loads(command('runtime-command',['powershell','-NoProfile','-Command',f"Get-CimInstance Win32_Process -Filter 'ProcessId = {int(before['pid'])}' | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"]))
assert 'runtime serve' in proc['CommandLine'] and '--port 0 --interval 2.0' in proc['CommandLine']
assert str(CORE/'tools/processforge.py').lower() in proc['CommandLine'].lower()
owned={x['relative_path'] for x in old['files']}
unowned={str(p.relative_to(CORE)):sha(p) for p in CORE.rglob('*') if p.is_file() and p.relative_to(CORE).parts[0] not in {'runtime','.git'} and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'} and p.relative_to(CORE).as_posix() not in owned and p.name!='processforge-core.manifest.json'}
result={'started_at':datetime.now(timezone.utc).isoformat(),'user_authorization':'explicit Core update and standard PF updater request','archive':str(archive),'archive_sha256':sha(archive),'prior_instance':before['instance_id'],'prior_pid':before['pid'],'unowned_sha256':unowned}
backup=HERE/'pre-install';backup.mkdir()
for source,name in [(CORE/'processforge-core.manifest.json','old-manifest.json'),(CORE/'runtime/core-update/last-apply.json','previous-last-apply.json'),(WP/'runtime/pf-runtime/service.json','runtime-service.json')]: shutil.copy2(source,backup/name)
save('install.json',result)
command('runtime-stop',cli('runtime','stop','--workplace',WP,'--timeout','30'))
stopped=json.loads(command('runtime-stopped',cli('runtime','status','--workplace',WP,'--json')))
assert not stopped['runtime']['running']
result['runtime_stopped']=True;save('install.json',result)
applied=json.loads(command('core-update-apply',cli('core-update','apply','--core-root',CORE,'--archive',archive,'--workplace-root',WP,'--confirm')))
result['apply']=applied;save('install.json',result)
assert applied['status']=='applied'
manifest=json.loads((CORE/'processforge-core.manifest.json').read_text(encoding='utf-8'))
extracted=ROOT/'.pf/tmp/t10-installed-delivery-20260926/extracted'
assert manifest==json.loads((extracted/'processforge-core.manifest.json').read_text(encoding='utf-8'))
assert all(sha(CORE/x['relative_path'])==x['sha256'] for x in manifest['files'])
result['installed_hashes_verified']=len(manifest['files'])
update_backup=Path(applied['backup_dir'])
assert update_backup.resolve().is_relative_to((CORE/'runtime/core-update/backups').resolve())
assert json.loads((update_backup/'control/old-manifest.json').read_text(encoding='utf-8'))==old
assert json.loads((update_backup/'control/new-manifest.json').read_text(encoding='utf-8'))==manifest
old_files={x['relative_path']:x for x in old['files']}
assert set(applied['backed_up'])==set(plan['changed'])
assert all(sha(update_backup/rel)==old_files[name]['sha256'] for name,rel in applied['backed_up'].items())
assert all(sha(CORE/n)==h for n,h in unowned.items())
assert all(sha(Path(n))==h for n,h in build['protected_sha256'].items())
assert all(sha(Path(n))==h for n,h in build['frozen_sha256'].items())
assert all(sha(ROOT/n)==h for n,h in build['source_sha256'].items())
result['backup_hashes_verified']=len(applied['backed_up']);result['preservation']='PASS';save('install.json',result)
command('runtime-start',cli('runtime','start','--workplace',WP,'--port','0','--interval','2.0','--timeout','30','--json'))
after=json.loads(command('runtime-after',cli('runtime','status','--workplace',WP,'--json')))
assert after['runtime']['running'] and after['status']=='ready' and after['instance_id']!=before['instance_id']
result['new_instance']=after['instance_id'];result['new_pid']=after['pid'];save('install.json',result)
command('runtime-doctor',cli('runtime','doctor','--workplace',WP))
command('workplace-doctor',cli('doctor-workplace','--root',WP))
command('update-status',cli('core-update','status','--core-root',CORE))
monitor=json.loads(command('installed-monitor-json',cli('monitor','--workplace',WP,'--json')))
assert monitor['kind']=='pf.runtime.monitor'
command('installed-monitor-ascii',cli('monitor','--workplace',WP,'--once','--ascii','--no-color'))
for name in ['runtime_monitor','runtime_status_version_truth','runtime_singleton_orphan']:
    command('installed-smoke-'+name,[sys.executable,'-B',CORE/'tools'/('smoke_'+name+'.py')],cwd=CORE)
assert not (CORE/'runtime/core-update/in-progress.json').exists()
assert all(sha(Path(n))==h for n,h in build['protected_sha256'].items())
assert all(sha(Path(n))==h for n,h in build['frozen_sha256'].items())
assert all(sha(ROOT/n)==h for n,h in build['source_sha256'].items())
assert all(sha(CORE/n)==h for n,h in unowned.items())
result['finished_at']=datetime.now(timezone.utc).isoformat();save('install.json',result)
print(json.dumps({'update_id':applied.get('update_id'),'backup':applied['backup_dir'],'installed_hashes':result['installed_hashes_verified'],'new_pid':after['pid'],'preservation':result['preservation']}),flush=True)
