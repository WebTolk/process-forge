from work import *
from inventory import TARGETS, collect
import re, os
from urllib.parse import unquote

def definitions():
    run=yaml.safe_load((ROOT/'.pf/runs'/RUN/'run.yaml').read_text(encoding='utf-8-sig'))
    return run['process_execution']['definition']

def write_index():
    d=definitions()
    rows=['# Complete artifact set','',
          'This is the current artifact-completion Work. Artifact status is ready_for_review with explicit primary-agent self-review; no human approval is implied. Historical delivery evidence is linked in [coverage.md](coverage.md).','',
          '[Project classification confirmation](project-classification-addendum.md) supplies the reviewed interpretation of the generated onboarding reports.','',
          '## Artifacts by stage','', '| Stage | Artifact | Requirement |','| --- | --- | --- |']
    defs={x['id']:x for x in d['artifact_definitions']}
    used=set()
    for st in d['stages']:
        for aid in st['produced_artifacts']:
            if aid in used:continue
            used.add(aid)
            name=REVISIONS.get(aid,aid)+'.md'
            rows.append(f'| {st["id"]} | [{aid}]({name}) | {"required" if defs[aid]["required"] else "conditional; applicability stated"} |')
    rows += ['', '## Provenance and correction','',
        'The first orchestration text passed through a PowerShell ASCII pipe and lost non-ASCII characters. Its three original files remain unchanged because a transition recorded their hashes. The effective task-record, execution-context-summary and lifecycle-mode-decision are the readable r02 files linked above and attached as normal intake evidence. Do not use the damaged first capture as current instructions.','',
        '[Baseline](baseline.json) and before/ retain original project reports and protected-file hashes. [Coverage JSON](coverage.json) records existing evidence, including pre-existing older hash differences. Private helpers reproduce the inventory and checks; they are not product changes.','']
    (HERE/'README.md').write_text('\n'.join(rows),encoding='utf-8',newline='\n')

def validate(label, required_stages=None, allow_future=False):
    d=definitions(); ids={aid for st in d['stages'] if required_stages is None or st['id'] in required_stages for aid in st['produced_artifacts']}
    all_effective={REVISIONS.get(x['id'],x['id'])+'.md' for x in d['artifact_definitions']}
    checked=[]; errors=[]; deferred=[]
    for aid in sorted(ids):
        p=HERE/(REVISIONS.get(aid,aid)+'.md')
        if not p.is_file(): errors.append('missing artifact '+aid);continue
        s=p.read_text(encoding='utf-8')
        if '???' in s or '\ufffd' in s or re.search(r'<(?:id|summary|artifact content|title)>|checksum: pending',s): errors.append('placeholder/encoding '+aid)
        try: body=s.split('## Content\n\n',1)[1].split('\n## Review\n',1)[0]
        except IndexError: errors.append('missing template section '+aid);continue
        expected=re.search(r'^- checksum: sha256:([a-f0-9]{64})$',s,re.M)
        if not expected or hashlib.sha256(body.encode('utf-8')).hexdigest()!=expected[1]: errors.append('body checksum '+aid)
        if len(body.strip())<100: errors.append('insufficient content '+aid)
        checked.append(p)
    checks=checked+[ROOT/'.pf/artifacts'/n for n in TARGETS]+[HERE/'README.md',HERE/'coverage.md',HERE/'project-classification-addendum.md']
    for p in (ROOT/'.pf/reviews/artifact-completion-20260927.md',ROOT/'.pf/handoffs/artifact-completion-20260927.md'):
        if p.is_file(): checks.append(p)
    for p in checks:
        s=p.read_text(encoding='utf-8')
        for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)',s):
            if re.match(r'[a-z]+://|#',link): continue
            target=(p.parent/unquote(link.split('#')[0])).resolve()
            if not target.exists():
                if allow_future and ((target.parent==HERE and target.name in all_effective) or target==ROOT/'.pf/handoffs/artifact-completion-20260927.md'):
                    deferred.append(str(target.relative_to(ROOT)));continue
                errors.append('broken link '+str(p.relative_to(ROOT))+' -> '+link)
        if p.name in TARGETS and (p.parent==ROOT/'.pf/artifacts'):
            if re.search(r'Unknown until reviewed|None yet|<artifact|\?\?\?',s): errors.append('root placeholder '+p.name)
            if re.search(r'(?i)[A-Z]:[\\/]',s): errors.append('machine path in report '+p.name)
    b=json.loads((HERE/'baseline.json').read_text(encoding='utf-8'))
    for group in ('protected','public_files'):
        for name,h in b[group].items():
            p=ROOT/name
            if not p.is_file() or sha(p)!=h: errors.append('preservation '+name)
    assert sha(CAP)==CAP_SHA
    if required_stages is None:
        a=yaml.safe_load((ROOT/'.pf/assignments'/(ASSIGN+'.yaml')).read_text(encoding='utf-8-sig'))
        for st in a.get('stage_history',[]):
            for ev in st.get('evidence',[]):
                if ev.get('path') and ev.get('sha256'):
                    p=ROOT/ev['path']
                    if not p.is_file() or sha(p)!=ev['sha256'].removeprefix('sha256:'):
                        errors.append('current Work evidence changed '+ev['path'])
    report,_=collect()
    current=report['current_delivery']
    for r in current:
        for a in r['artifacts']:
            if a['required'] and not a['evidence']:errors.append('mandatory historical ID '+a['artifact_id'])
    errors += [str(x) for x in report['historical_reference_findings'] if x['current']]
    # Validate path literals in the new responsibility map against the actual checkout.
    for p in re.findall(r'`((?:src/|bin/|tools/|packs/|processes/|packages/|schemas/|templates/|docs/|prompts/|examples/|seeds/|checksums/|dist/|updates/)[^`]+)`',(ROOT/'.pf/artifacts/repository-map.md').read_text(encoding='utf-8')):
        if '*' in p: continue
        if not (ROOT/p).exists(): errors.append('repository map path '+p)
    result={'time':now(),'status':'pass' if not errors else 'fail','artifact_count':len(checked),'current_delivery_runs':len(current),'required_delivery_bindings':sum(a['required'] for r in current for a in r['artifacts']),'protected_files':len(b['protected']),'tracked_public_files':len(b['public_files']),'deferred_future_links':sorted(set(deferred)),'preexisting_historical_hash_findings':len(report['historical_reference_findings']),'errors':errors}
    save(label+'.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    assert not errors, errors
    return result

if __name__=='__main__':
    write_index()
    if '--complete' in sys.argv: validate('verification-final')
    else: validate('verification-assurance',{'orchestration','intake-scope','investigation','domain-modeling','architecture-plan','implementation'},True)
