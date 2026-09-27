"""Qualify a clean candidate without altering the dirty main checkout."""
import importlib.util, shutil, zipfile
from work import *

BASE='69110c50559d994d7a31e751b7cd7afc989698db'
OLD=ROOT/'.pf/tmp/t06-installed-delivery-20260926/candidate'
CANDIDATE=ROOT/'.pf/tmp/t10-installed-delivery-20260926/candidate'
EXTRACTED=CANDIDATE.parent/'extracted'
EXPECTED={'tools/pf_runtime/monitor.py','tools/pf_runtime/service.py','tools/processforge.py','tools/smoke_runtime_monitor.py','docs/concepts/runtime-monitor.md','docs/ru/concepts/runtime-monitor.md','docs/concepts/runtime-mcp.md','docs/ru/concepts/runtime-mcp.md','checksums/processforge.sha256'}
assert state('build-work-state')['stage']['id']=='implementation'
assert not CANDIDATE.exists() and not (HERE/'build.json').exists()
spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/validate-process-forge-checksums.py')
inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
files={p.relative_to(ROOT).as_posix():p for p in inv.public_files(ROOT)+[ROOT/'checksums/processforge.sha256']}
prior={p.relative_to(OLD).as_posix():p for p in inv.public_files(OLD)+[OLD/'checksums/processforge.sha256']}
delta={n for n,p in files.items() if n not in prior or inv.released_content(p)!=inv.released_content(prior[n])}
assert delta==EXPECTED,(sorted(delta),sorted(EXPECTED))
assert not (set(prior)-set(files))
accepted=json.loads((ROOT/'.pf/artifacts/t10-monitor-20260926/assurance-results.json').read_text(encoding='utf-8'))
assert all(sha(ROOT/n)==h for n,h in accepted['source_hashes'].items())
old=json.loads((CORE/'processforge-core.manifest.json').read_text(encoding='utf-8'))
assert all(sha(CORE/x['relative_path'])==x['sha256'] for x in old['files'])
protected=[ROOT/'.pf/contexts/project-context.snapshot.yaml',CAP,WP/'workplace.yaml',WP/'terms.yaml',ROOT/'.codex/hooks.json',Path('C:/Users/musst/.codex/config.toml')]
for rel in ['registries','runtime-drivers','mcp','tools','specializations','platform-contracts']:
    protected.extend(p for p in (WP/rel).rglob('*') if p.is_file() and p.suffix in {'.yaml','.yml','.json','.toml','.md'})
frozen={str(p):sha(p) for p in (ROOT/'.pf/artifacts').rglob('*') if p.is_file() and p.parts[len(ROOT.parts)+2].startswith(('t01-','t02-','t03-','t04-','t05-','t06-','t07-','t08-','t09-','t10-monitor-'))}
result={'started_at':datetime.now(timezone.utc).isoformat(),'main_head':command('main-head',['git','rev-parse','HEAD']).strip(),'source_sha256':{n:sha(p) for n,p in files.items()},'protected_sha256':{str(p):sha(p) for p in protected if p.is_file()},'frozen_sha256':frozen,'old_manifest':old,'delta':sorted(delta)}
save('baseline.json',result)
command('main-status',['git','status','--porcelain'])
CANDIDATE.parent.mkdir(parents=True)
command('candidate-create',['git','worktree','add','--detach',CANDIDATE,BASE])
for name in sorted(delta):
    target=CANDIDATE/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
assert {p.relative_to(CANDIDATE).as_posix() for p in inv.public_files(CANDIDATE)+[CANDIDATE/'checksums/processforge.sha256']}==set(files)
assert all(inv.released_content(p)==inv.released_content(CANDIDATE/n) for n,p in files.items())
command('candidate-add',['git','add','--',*sorted(delta)],cwd=CANDIDATE)
command('candidate-diff-check',['git','diff','--cached','--check'],cwd=CANDIDATE)
command('candidate-commit',['git','commit','-m','Deliver the read-only terminal Runtime monitor'],cwd=CANDIDATE)
result['candidate_commit']=command('candidate-head',['git','rev-parse','HEAD'],cwd=CANDIDATE).strip()
result['candidate_tree']=command('candidate-tree',['git','rev-parse','HEAD^{tree}'],cwd=CANDIDATE).strip()
assert not command('candidate-status',['git','status','--porcelain'],cwd=CANDIDATE).strip()
result['candidate_clean']=True;save('build.json',result)
for name,args in [('checksums',['--check']),('schemas',[]),('public-cleanliness',[])]:
    tool={'checksums':'validate-process-forge-checksums','schemas':'validate-process-forge-schemas','public-cleanliness':'validate-public-cleanliness'}[name]
    command('candidate-'+name,[sys.executable,'-B',CANDIDATE/'tools'/(tool+'.py'),*args],cwd=CANDIDATE)
for name in ['runtime_monitor','runtime_singleton_orphan','runtime_status_version_truth','runtime_scheduler_failure_isolation','runtime_no_domain_file_patterns','docs_agent_no_manual_infra','docs_mcp_host_owned_stdio','docs_codex_hooks_optional']:
    command('candidate-smoke-'+name,[sys.executable,'-B',CANDIDATE/'tools'/('smoke_'+name+'.py')],cwd=CANDIDATE)
archive=HERE/'delivery-package'/('processforge-1.1.0-t10-'+result['candidate_commit'][:8]+'.zip')
command('release-pack',[sys.executable,'-B',CANDIDATE/'bin/pf.py','release-pack','--root',CANDIDATE,'--output',archive],cwd=CANDIDATE)
result['archive']=str(archive);result['archive_sha256']=sha(archive);save('build.json',result)
command('release-archive-test',[sys.executable,'-B',CANDIDATE/'bin/pf.py','release-archive-test','--root',CANDIDATE,'--archive',archive,'--extracted-test','quick'],cwd=CANDIDATE)
with zipfile.ZipFile(archive) as z: z.extractall(EXTRACTED)
manifest=json.loads((EXTRACTED/'processforge-core.manifest.json').read_text(encoding='utf-8'))
assert all(sha(EXTRACTED/x['relative_path'])==x['sha256'] and (EXTRACTED/x['relative_path']).stat().st_size==x['size'] for x in manifest['files'])
result['archive_files_verified']=len(manifest['files'])
command('extracted-monitor',[sys.executable,'-B',EXTRACTED/'tools/smoke_runtime_monitor.py'],cwd=EXTRACTED)
plan=json.loads(command('core-update-plan',cli('core-update','plan','--core-root',CORE,'--archive',archive,'--workplace-root',WP)))
assert not plan['blockers'] and not plan['removed'] and not plan['locally_modified']
assert set(plan['changed'])|set(plan['added'])==EXPECTED
assert plan['workplace_migration']['status']=='not_applicable' and not plan['workplace_migration']['operations']
assert all(sha(ROOT/n)==h for n,h in result['source_sha256'].items())
assert all(sha(Path(n))==h for n,h in result['protected_sha256'].items())
assert all(sha(Path(n))==h for n,h in result['frozen_sha256'].items())
result['plan_counts']=plan['counts'];result['finished_at']=datetime.now(timezone.utc).isoformat();save('build.json',result)
print(json.dumps({k:result[k] for k in ['candidate_commit','archive','archive_sha256','archive_files_verified','plan_counts']}),flush=True)
