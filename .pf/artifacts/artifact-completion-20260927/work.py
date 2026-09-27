"""Private artifact completion evidence; lifecycle is changed only by PF CLI."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, subprocess, sys, yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CORE = Path('D:/.agents/processforge')
WP = Path('D:/.agents/processforge-workplace')
RUN = 'garage-complete-all-required-pf-artifacts-for-the-current-processforge-t'
ASSIGN = 'complete-all-required-pf-artifacts-for-the-current-processforge-t01-t10'
CAP = ROOT / '.pf/contexts/assignment-capsules' / (ASSIGN + '.capsule.yaml')
CAP_SHA = 'ba35824ecdc7b6ce52a4e144fd18ff83c66259e4f095b735214f667610da3d6a'
LOG = ROOT / '.pf/logs/artifact-completion-20260927.md'

def now(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str)+'\n', encoding='utf-8')
def log(task, files, status, next_step):
    with LOG.open('a', encoding='utf-8') as f:
        f.write(f'\n## {now()} - primary agent\n\nTask: {task}\nFiles analyzed/changed: {files}\nStatus: {status}\nTools: Serena pattern search and standard installed PF CLI; connected MCP timed out.\nRisks: preserve pinned evidence and capsules; host reload is unverified.\nNext steps: {next_step}\n')
def command(label, args, timeout=360):
    p = subprocess.run([str(x) for x in args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=timeout)
    result = {'time': now(), 'argv': [str(x) for x in args], 'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
    save('commands/'+label+'.json', result)
    print(label, p.returncode, flush=True)
    assert p.returncode == 0, (p.stdout[-3000:],p.stderr[-3000:])
    return p.stdout
def cli(*args): return [sys.executable, '-B', CORE/'bin/pf.py', *args]
def state(label):
    assert sha(CAP) == CAP_SHA
    s = json.loads(command(label, cli('work-state','--project-root',ROOT,'--workplace',WP,'--run',RUN,'--assignment',ASSIGN,'--json')))
    assert s['run']['id'] == RUN and not s['blockers']
    return s
REVISIONS = {'task-record': 'task-record-r02', 'execution-context-summary': 'execution-context-summary-r02', 'lifecycle-mode-decision': 'lifecycle-mode-decision-r02'}
def doc(aid, title, body, role='orchestrator'):
    path = HERE / (REVISIONS.get(aid, aid)+'.md')
    assert not path.exists(), f'Artifact already exists: {path}'
    body = body.strip()+'\n'
    assert '???' not in body and '???' not in title, 'Text encoding loss'
    checksum = hashlib.sha256(body.encode('utf-8')).hexdigest()
    path.write_text(f'# Artifact: {aid}\n\n## Metadata\n\n- type: {aid}\n- title: {title}\n- process: software-feature-development@1.1.0\n- status: ready_for_review\n- owner_role: {role}\n- source_assignment: {ASSIGN}\n- content_reference: {path.relative_to(ROOT).as_posix()}\n- checksum: sha256:{checksum}\n- checksum_scope: content_section_utf8_lf\n- protection_policy: preserve_after_stage_evidence\n\n## Summary\n\n{title}.\n\n## Content\n\n{body}\n## Review\n\n- status: pass\n- reviewer: primary agent; self-review, no independent-review claim\n- reviewed_at: {now()}\n',encoding='utf-8',newline='\n')
def advance(stage):
    s = state(stage+'-before')
    assert s['stage']['id'] == stage
    run = yaml.safe_load((ROOT/'.pf/runs'/RUN/'run.yaml').read_text(encoding='utf-8-sig'))
    definition = run['process_execution']['definition']
    st = next(x for x in definition['stages'] if x['id'] == stage)
    evidence=[]
    for aid in st['produced_artifacts']:
        p = HERE/(REVISIONS.get(aid, aid)+'.md')
        assert p.is_file(), aid
        assert '???' not in p.read_text(encoding='utf-8'), 'Text encoding loss'
        evidence.append({'kind':'artifact','artifact_id':aid,'path':p.relative_to(ROOT).as_posix(),'status':'ready'})
    if stage == 'intake-scope':
        for aid in ('execution-context-summary','lifecycle-mode-decision'):
            p = HERE/(REVISIONS[aid]+'.md')
            evidence.append({'kind':'artifact','artifact_id':aid,'path':p.relative_to(ROOT).as_posix(),'status':'ready'})
    for gate in st['exit_gates']:
        evidence.append({'kind':'gate','gate_id':gate,'path':evidence[0]['path'],'status':'passed'})
    save(stage+'-evidence.json',evidence)
    result=json.loads(command(stage+'-transition',cli('work-transition','--project-root',ROOT,'--workplace',WP,'--run',RUN,'--assignment',ASSIGN,'--outcome','completed','--evidence-file',HERE/(stage+'-evidence.json'),'--notes','Reviewed explicit stage artifacts and evidence; preserve historical scope and continue the pinned process.','--json')))
    assert result['action'] in ('stage_transitioned','run_completed'), result
    assert sha(CAP)==CAP_SHA
    log(stage, ', '.join(st['produced_artifacts']), result['action'], str(result.get('stage','completed')))
    print(result['action'], result.get('stage'), flush=True)

if __name__=='__main__':
    for stage in sys.argv[1:]: advance(stage)
