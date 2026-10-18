from datetime import datetime, timezone
import hashlib, importlib.util, json, shutil, subprocess, sys, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
CANDIDATE=ROOT/'.pf/tmp/t06-installed-delivery-20260926/candidate'
EXTRACTED=ROOT/'.pf/tmp/t06-installed-delivery-20260926/extracted-corrected'
prior=json.loads((HERE/'candidate-build.json').read_text())
result={'started_at':datetime.now(timezone.utc).isoformat(),'prior_candidate':prior['candidate_commit'],'commands':[]}
def save():
    (HERE/'candidate-corrected.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
def run(argv,cwd=CANDIDATE,timeout=600):
    p=subprocess.run(list(map(str,argv)),cwd=cwd,capture_output=True,text=True,encoding='utf-8',timeout=timeout)
    result['commands'].append({'argv':list(map(str,argv)),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr});save()
    assert p.returncode==0,p.stderr[-3000:]+p.stdout[-3000:]
    return p.stdout.strip()
assert run(['git','rev-parse','HEAD'])==prior['candidate_commit']
assert not run(['git','status','--porcelain'])
changed=['docs/concepts/diagnostics.md','docs/ru/concepts/diagnostics.md','checksums/processforge.sha256']
actual=[name for name,digest in prior['source_raw_sha256'].items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
assert sorted(actual)==sorted(changed),actual
for name in changed:shutil.copyfile(ROOT/name,CANDIDATE/name)
run([sys.executable,'-B','tools/smoke_docs_current_code_contract.py'])
run([sys.executable,'-B','tools/validate-process-forge-checksums.py','--check'])
run(['git','add','--',*changed]);run(['git','diff','--cached','--check'])
run(['git','commit','-m','Use executable diagnostics CLI examples in English and Russian'])
result['candidate_commit']=run(['git','rev-parse','HEAD'])
result['candidate_tree']=run(['git','rev-parse','HEAD^{tree}'])
assert not run(['git','status','--porcelain']);result['candidate_clean']=True
archive=HERE/'delivery-package'/('processforge-1.1.0-t06-'+result['candidate_commit'][:8]+'.zip')
result['archive']=str(archive)
run([sys.executable,'-B','bin/pf.py','release-pack','--root',CANDIDATE,'--output',archive])
result['archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest();save()
run([sys.executable,'-B','bin/pf.py','release-archive-test','--root',CANDIDATE,'--archive',archive,'--extracted-test','quick'])
assert not EXTRACTED.exists()
with zipfile.ZipFile(archive) as z:z.extractall(EXTRACTED)
before=json.loads((ROOT/'.pf/tmp/t06-installed-delivery-20260926/extracted/processforge-core.manifest.json').read_text())
after=json.loads((EXTRACTED/'processforge-core.manifest.json').read_text())
old={x['relative_path']:x for x in before['files']};new={x['relative_path']:x for x in after['files']}
assert old.keys()==new.keys()
delta=[]
for name,item in new.items():
    raw=(EXTRACTED/name).read_bytes()
    assert len(raw)==item['size'] and hashlib.sha256(raw).hexdigest()==item['sha256'],name
    if item['sha256']!=old[name]['sha256']:delta.append(name)
assert sorted(delta)==sorted(changed),delta
result['payload_changes_from_tested_candidate']=delta
result['payload_hashes_verified']=len(new)
result['reused_unchanged_feature_passes']=21
run([sys.executable,'-B',EXTRACTED/'tools/smoke_docs_current_code_contract.py'],cwd=EXTRACTED)
assert run(['git','rev-parse','HEAD'],cwd=ROOT)==prior['main_head']
result['source_raw_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in prior['source_raw_sha256']}
result['finished_at']=datetime.now(timezone.utc).isoformat();save()
print(json.dumps({k:result[k] for k in ['candidate_commit','candidate_tree','archive','archive_sha256','payload_hashes_verified','payload_changes_from_tested_candidate']}),flush=True)
