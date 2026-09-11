from pathlib import Path
import json, yaml

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
PREFIX=BASE.relative_to(ROOT).as_posix()
WORKERS=['f0304-evidence','f05-completion','f0305-assurance','f0305-review']
def write(name,content):
    (BASE/name).write_text(content,encoding='utf-8')
def dump(name,value):write(name,json.dumps(value,indent=2)+'\n')
statuses={name:yaml.safe_load((ROOT/'.pf/assignments'/f'{name}.yaml').read_text(encoding='utf-8'))['status'] for name in WORKERS}
assert all(value=='done' for value in statuses.values()),statuses
for name in ['shell-doctor','carrier-doctor']:
    assert json.loads((BASE/(name+'.json')).read_text())['exit_code']==0,name
for name in ['f0305-assurance','f0305-review']:
    assert 'PASS' in (BASE/name/'report.md').read_text(encoding='utf-8'),name
report=(BASE/'integration-report.md').read_text(encoding='utf-8')
report=report.replace('Status: implementation and primary validation accepted; independent assurance/review and PF closeout pending.','Status: F03-F05 accepted after primary validation and independent assurance/review. Governed terminal states are recorded in closeout.json.')
report+='\n## Independent acceptance\n\nBoth `f0305-assurance/report.md` and `f0305-review/report.md` give bounded PASS. Four worker assignments are collected DONE. Final schema and public-cleanliness checks pass. Shell and carrier run doctors pass. See closeout.json for terminal lifecycle confirmation.\n'
write('integration-report.md',report)
write('execution-record.md','# F03-F05 execution record\n\nAll four bounded shell assignments are collected DONE. Primary implemented acceptance corrections and verified genuine positive/negative temporary-fixture results. Independent assurance and review give bounded PASS.\n\n'+ '\n'.join(f'- {name}: {status}; report: {PREFIX}/{name}/report.md' for name,status in statuses.items())+'\n\nDetails: integration-report.md; orchestration log .pf/logs/core-f03-f05-orchestrator-20260910.md.\n')
write('final-review.md','# Final F03-F05 review\n\nResult: PASS for this bounded remediation scope.\n\nIndependent assurance/review: f0305-assurance/report.md and f0305-review/report.md. Both workers are collected DONE; raw primary evidence and rejected attempts remain available.\n\nRun doctors: shell-doctor.json and carrier-doctor.json, exit 0. Source/public-copy regression matrices and baseline negative controls passed their expected outcomes. Final schema/cleanliness/checksum and preservation checks passed.\n\nF06-F12, Runtime startup baseline failure and release qualification remain separate. No keyed tamper-resistance or exactly-once hooks are claimed.\n')
write('summary.md','# F03-F05 summary\n\nF03-F05 are accepted in current source after primary tests and independent assurance/review.\n\n- Latest applicable evidence controls readiness; selected file evidence is revalidated.\n- Terminal completion is journaled and recoverable through ordinary transition/complete calls.\n- Eighteen before/after failure points, corruption cases, public-copy and original-module negative controls verified.\n- Ten related checks, final terminal/events, schema/cleanliness/checksum/preservation pass.\n- Four PF shell assignments on gpt-5.6-luna are collected DONE.\n\nNo commit, publication or installed update. F06-F12 and the baseline Runtime startup blocker remain. Full source/archive/extracted release qualification is not claimed.\n\nIntegration: integration-report.md. Final PF terminal statuses: closeout.json. Next-owner handoff: .pf/handoffs/core-f03-f05-20260910.md.\n')
handoff='''# Handoff: primary orchestrator -> next remediation owner

Objective: Repair Python-core audit F03-F05 through governed sequential junior PF shell workers.
Current status: F03-F05 accepted; genuine primary regression and portability checks PASS; independent assurance/review PASS; four workers collected DONE. Final run terminal confirmation is in .pf/artifacts/core-f03-f05-20260910/closeout.json.
Input artifacts: .pf/artifacts/core-f03-f05-20260910/integration-report.md; f0304-final-isolated-results.json; final-evidence.json; f05-matrix-2.json; final-public-results.json; related-results.json; final-terminal.json; final-events.json; final-review.md; source-preservation.json.
Files changed: src/processforge_core/process_execution.py; tools/smoke_work_evidence_freshness.py; tools/smoke_work_completion_recovery.py; two test registrations in tools/processforge.py; checksums/processforge.sha256; this scope's private governance and evidence.
Files not to touch: Accepted F01/F02 and previous docs/required-output changes; historical audit outputs and immutable capsules; installed Core/Workplace; unrelated historical runs and dist archives.
Known issues: F06-F12 remain open. Prior full source run stopped at Runtime startup, 45 PASS / 1 FAIL, reproduced on clean baseline 1aecc18b. This batch did not rerun/qualify the whole release suite. Evidence hashes retain normal filesystem TOCTOU; completion is recoverable rather than an atomic multi-file read snapshot; hook dispatch can repeat; intent checksum is corruption detection, not hostile-writer authentication.
Required checks: Remediate F06-F12 in bounded governed scopes, diagnose Runtime in isolated fixture, then full source and clean candidate/archive/extracted qualification. Preserve current accepted source bytes and negative controls.
Next recommended action: F06-F08 (live-owner registry locking and two NameErrors) with one writer for tools/processforge.py; separately plan updater/index/ingress F09-F12. No commit/push/publication/installed update has been performed.
'''
(ROOT/'.pf/handoffs/core-f03-f05-20260910.md').write_text(handoff,encoding='utf-8')
def artifact(identifier,path):return {'kind':'artifact','artifact_id':identifier,'status':'ready','path':path}
def gate(identifier,summary):return {'kind':'gate','gate_id':identifier,'status':'passed','summary':summary}
dump('execution-evidence.json',[artifact('task-iteration-log',f'{PREFIX}/execution-record.md'),gate('task-results-recorded','Four shell assignments DONE; primary tests and independent assurance/review recorded.')])
dump('result-evidence.json',[artifact('task-result',f'{PREFIX}/integration-report.md'),gate('all-blocking-tasks-completed','All four delegated assignments DONE. F03-F05 accepted with genuine tests and independent review; release boundaries retained.')])
dump('review-evidence.json',[artifact('run-review',f'{PREFIX}/final-review.md'),gate('run-doctor-passed','Shell and carrier run doctors exit 0; independent bounded reviews PASS.')])
dump('summary-evidence.json',[artifact('run-summary',f'{PREFIX}/summary.md'),artifact('run-handoff','.pf/handoffs/core-f03-f05-20260910.md'),gate('run-summary-created','Summary and next-remediation handoff preserve F06-F12 and the separate Runtime/release boundary.')])
print('Final accepted reports, handoff and four stage-evidence files prepared.')
