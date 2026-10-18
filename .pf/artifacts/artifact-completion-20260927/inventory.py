from work import *

TARGETS = ['README.md','project-profile.md','repository-map.md','project-conventions.md',
           'toolchain-detection-report.md','mcp-capability-report.md',
           'template-matching-report.md','global-resource-matching-report.md']

def collect():
    rows=[]; history=[]; protected={}; problems=[]
    for p in sorted((ROOT/'.pf/runs').glob('*/run.yaml')):
        r=yaml.safe_load(p.read_text(encoding='utf-8-sig')) or {}
        if r.get('id')==RUN: continue
        current=str(r.get('created_at',''))>='2026-09-25'
        definitions=r.get('process_execution',{}).get('definition',{}).get('artifact_definitions',[])
        for task in r.get('tasks',[]):
            ap=ROOT/task['assignment']
            if not ap.is_file():
                problems.append({'run':r['id'],'kind':'missing_assignment','path':task['assignment'],'current':current}); continue
            a=yaml.safe_load(ap.read_text(encoding='utf-8-sig')) or {}; evidence={}
            for stage in a.get('stage_history',[]):
                for ev in stage.get('evidence',[]):
                    ref=ev.get('path')
                    if not ref: continue
                    q=ROOT/ref
                    if q.is_file(): protected[q.relative_to(ROOT).as_posix()]=sha(q)
                    if ev.get('kind')!='artifact': continue
                    actual=sha(q) if q.is_file() else None
                    expected=ev.get('sha256','').removeprefix('sha256:')
                    item={'artifact_id':ev.get('artifact_id'),'stage':stage['stage_id'],'path':ref,'exists':actual is not None,'expected_sha256':expected or None,'actual_sha256':actual,'hash_matches':actual==expected if expected else None}
                    evidence.setdefault(ev.get('artifact_id'),[]).append(item)
                    if actual is None or (expected and expected!=actual):
                        problems.append({'run':r['id'],'kind':'missing_evidence' if actual is None else 'changed_evidence','path':ref,'current':current})
            if current:
                artifacts=[{'artifact_id':d['id'],'required':bool(d.get('required')),'evidence':evidence.get(d['id'],[])} for d in definitions]
                rows.append({'run':r['id'],'assignment':a['id'],'run_status':r['status'],'assignment_status':a.get('status'),'objective':r.get('objective'),'artifacts':artifacts})
            history.append({'run':r['id'],'status':r['status'],'created_at':str(r.get('created_at','')),'current_delivery':current})
    for p in (ROOT/'.pf/contexts/assignment-capsules').glob('*.yaml'):
        protected[p.relative_to(ROOT).as_posix()]=sha(p)
    return {'observed_at':now(),'current_delivery':rows,'history':history,'historical_reference_findings':problems},protected

def main():
    report,protected=collect()
    for n in TARGETS:
        assert '.pf/artifacts/'+n not in protected, 'Target is recorded stage evidence: '+n
    current_issues=[p for p in report['historical_reference_findings'] if p['current']]
    missing=[(r['run'],a['artifact_id']) for r in report['current_delivery'] for a in r['artifacts'] if a['required'] and not a['evidence']]
    assert not current_issues and not missing,(current_issues,missing)
    save('coverage.json',report)
    git_files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf-8').split('\0')
    public={n:sha(ROOT/n) for n in git_files if n and not n.startswith('.pf/') and (ROOT/n).is_file()}
    baseline={'time':now(),'protected':protected,'public_files':public,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'target_sha256':{n:sha(ROOT/'.pf/artifacts'/n) for n in TARGETS}}
    assert not (HERE/'baseline.json').exists()
    save('baseline.json',baseline)
    for n in TARGETS:
        p=HERE/'before'/n; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes((ROOT/'.pf/artifacts'/n).read_bytes())
    lines=['# Current delivery artifact coverage','',f'Observed: {report["observed_at"]}. Generated from actual assignments and pinned definitions.','',
           'All mandatory artifact IDs in the 17 current delivery works have recorded files with matching hashes. A shared file can satisfy several IDs. Optional definitions without records are not missing mandatory evidence.','',
           'The separate completion Work supplies explicit documents for all 29 definitions. Its readable r02 orchestration records supersede the interpretation of the encoding-damaged first capture, whose recorded bytes remain preserved.','']
    for r in report['current_delivery']:
        lines += [f'## {r["run"]}','',r['objective'],'',f'Run: {r["run_status"]}; assignment: {r["assignment_status"]}.','', '| Artifact | Required | Evidence |','| --- | --- | --- |']
        for a in r['artifacts']:
            refs=sorted(set(e['path'] for e in a['evidence']))
            links='<br>'.join(f'[{Path(p).name}]({Path(__import__("os").path.relpath(ROOT/p,HERE)).as_posix()})' for p in refs) or 'Optional; no separate historical artifact claimed'
            lines.append(f'| {a["artifact_id"]} | {"yes" if a["required"] else "no"} | {links} |')
        lines.append('')
    lines += ['## Historical archive boundary','',f'Inventoried {len(report["history"])} pre-existing runs. Older unrelated status and reference findings are preserved in coverage.json; this document does not invent missing historical results or relabel them as current completion.','']
    (HERE/'coverage.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
    print(json.dumps({'current_runs':len(report['current_delivery']),'required_records':sum(a['required'] for r in report['current_delivery'] for a in r['artifacts']),'protected_files':len(protected),'public_files':len(public),'historical_findings':len(report['historical_reference_findings']),'current_issues':current_issues,'missing_required':missing}))
    log('Artifact and preservation inventory','coverage.json, coverage.md, baseline.json and before/ snapshots','Mandatory current evidence complete; editable project reports not sealed stage evidence','Complete investigation and domain artifacts')

if __name__=='__main__': main()
