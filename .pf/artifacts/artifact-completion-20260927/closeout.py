from work import *
from validate_artifacts import validate,write_index

s=state('completed-state')
assert s['action']=='run_completed' and s['run']['status']=='completed' and s['assignment']['status']=='done'
out=command('final-run-doctor',cli('run-doctor','--project-root',ROOT,'--run',RUN))
assert 'FAIL:' not in out
a=yaml.safe_load((ROOT/'.pf/assignments'/(ASSIGN+'.yaml')).read_text(encoding='utf-8-sig'))
latest={}
for st in a['stage_history']:
    for ev in st.get('evidence',[]):
        if ev.get('kind')=='artifact':latest[ev['artifact_id']]=ev['path']
assert len(latest)==29
for aid,name in REVISIONS.items(): assert latest[aid].endswith(name+'.md')

handoff=ROOT/'.pf/handoffs/artifact-completion-20260927.md'
handoff.write_text(f'''# Handoff: artifact-completion -> project maintainer

Objective: Complete required .pf artifacts and current project knowledge after the T01-T10 delivery.

Current status: Work completed through all nine pinned stages; assignment done. All 29 effective artifact definitions are filled. Final run-doctor: {out.count('PASS:')} PASS, no FAIL.

Input artifacts:
- [Current artifact index](../artifacts/README.md)
- [Complete Work set](../artifacts/artifact-completion-20260927/README.md)
- [Coverage matrix](../artifacts/artifact-completion-20260927/coverage.md)
- [Final verification](../artifacts/artifact-completion-20260927/verification-final.json)
- [Review](../reviews/artifact-completion-20260927.md)

Files changed: Eight unsealed project reports, one full artifact bundle, review, handoff and append-only log; standard PF CLI generated the current Work lifecycle records.

Files not to touch: Historical evidence/capsules, earlier archives/backups, installed Core and unrelated source. Originals of the eight reports are retained under the bundle's before/ directory.

Known issues: Connected MCP timeout; doctor-project local-launcher warning; 26 pre-existing historical reference-hash differences. None is relabelled as repaired. The first orchestration capture lost text encoding; r02 revisions are the effective records and originals remain at recorded hashes. Native strict-egress routes remain unsupported.

Required checks: Completed artifact/link/hash/map/preservation checks, doctor-project, context freshness, final work-state and run-doctor. Source feature suites, browser, build, migration and installation are not_applicable to this documentation-only change.

Next recommended action: Ordinary project work from current context and the artifact index. No pending action remains in this artifact-completion Work; global policy proposals remain proposals.
''',encoding='utf-8',newline='\n')
review=ROOT/'.pf/reviews/artifact-completion-20260927.md'
text=review.read_text(encoding='utf-8')
text=text.replace('pass for the reviewed documentation through code-assurance. Final complete-set\nand lifecycle results are recorded separately in the bundle closeout.','pass. Complete-set verification covers all 29 effective artifacts; the Work\ncompleted through all nine stages. Final command results are in the bundle closeout.')
text=text.replace('No blocking defect found in the implemented documentation. Final remaining stage\nartifacts and the final Work transition must be verified before closeout.','No blocking defect remains in the documentation scope. All final stage artifacts\nand the final Work transition were verified.')
text=text.replace('Deliver the local documentation, finish the remaining pinned stages, and record\nthe full-set check. Leave original reviews and accepted historical reports intact.','Use the completed local documentation and current artifact index. Leave original\nreviews and accepted historical reports intact.')
review.write_text(text,encoding='utf-8',newline='\n')
write_index()
v=validate('verification-final')
assert v['artifact_count']==29 and not v['deferred_future_links']
close=f'''# Artifact completion closeout

Completed on {now()} through standard PF Work transitions.

- Run: `{RUN}`; action `run_completed`; assignment `done`.
- All nine stages completed. Final run-doctor: {out.count('PASS:')} PASS, zero FAIL.
- All 29 effective artifacts are substantive, self-reviewed and ready_for_review.
- Eight current project reports updated; originals retained under before/.
- 17 delivery works / 340 mandatory artifact-ID bindings have valid evidence.
- 661 protected evidence/capsule files and 966 tracked non-.pf files unchanged.
- Artifact body hashes, recorded Work hashes, relative links and map paths pass.
- Context after project-report edits: fresh, execution/resources ready.
- No product source, installed Core, service lifecycle or global policy update.

Evidence: [full set](README.md), [coverage](coverage.md),
[final verification](verification-final.json),
[doctor](commands/final-run-doctor.json),
[review](../../reviews/artifact-completion-20260927.md),
[handoff](../../handoffs/artifact-completion-20260927.md).

Residual facts: connected MCP timed out; doctor-project warns about the absent
local launcher in this source-distribution checkout; older evidence contains 26
pre-existing hash differences. Original T06 history and delivery boundaries are
preserved. Readable r02 orchestration records correct the first ASCII-damaged
capture without modifying its recorded bytes. These are explicit provenance and
operational limits, not unfilled current artifact requirements.
'''
(HERE/'closeout.md').write_text(close,encoding='utf-8',newline='\n')
save('completion.json',{'time':now(),'action':s['action'],'run':s['run'],'assignment':s['assignment'],'effective_artifact_ids':sorted(latest),'doctor_pass':out.count('PASS:'),'verification':v,'capsule_sha256':sha(CAP)})
log('Final artifact completion', 'closeout.md, completion.json, final review/handoff and final verification', 'run_completed; 29 effective artifacts; all checks passed within scope', 'No pending task; proposals remain unapplied')
print(close,flush=True)
