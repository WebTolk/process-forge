import json
from pathlib import Path
root=Path.cwd()
base=Path('.pf/artifacts/publish-f06-f08-20260910')
base.mkdir(parents=True,exist_ok=True)
run='garage-publish-validated-fixes-to-dev-remediate-python-core-audit-f06-f0'
plan=json.loads(Path('.pf/artifacts/core-f03-f05-20260910/orchestrator-plan.yaml').read_text())
plan['run']={'id':'core-f06-f08-shell-20260910','title':'F06-F08 registry ownership and optional CLI paths','process':'multi-agent-task-orchestration'}
workers=[]
for i,(wid,review) in enumerate([('f0608-cli',False),('f0608-review',True)]):
    w=dict(plan['workers'][2 if review else 0])
    w.update(id=wid,title=wid,objective=f'Execute bounded brief {base}/{wid}-brief.md',depends_on=['f0608-cli'] if review else [])
    w['allowed_files']=([f'{base}/{wid}/**',f'.pf/tmp/{wid}/**'] if review else ['tools/processforge.py','tools/smoke_cli_audit_f0608.py',f'{base}/{wid}/**',f'.pf/tmp/{wid}/**'])
    w['allowed_read_files']=['src/**','tools/**','docs/**','schemas/**','processes/**','templates/**','.pf/contexts/project-context.snapshot.yaml','.pf/artifacts/python-core-audit-20260908/**',f'{base}/**']
    w['forbidden_files']=['VERSION','CHANGELOG.md','checksums/**','.pf/process-forge.yaml','.pf/artifacts/python-core-audit-20260908/**']
    w['required_sources']=[f'{base}/{wid}-brief.md']
    w['required_outputs']=[{'id':wid+'-report','path':f'{base}/{wid}/report.md','type':'markdown','required':True}]
    w['expected_report_artifact']=f'{base}/{wid}/report.md'
    workers.append(w)
plan['workers']=workers
plan['integration']['expected_output']=f'{base}/integration-report.md'
plan['metadata']={'carrier_run':run,'authorization':'User requests commit/push dev, continued remediation by junior PF shell workers, and installed Core update/test. Primary owns installed update and acceptance. One source writer.'}
(base/'orchestrator-plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
(base/'f0608-cli-brief.md').write_text('''# F06-F08 implementation brief
Read the audit report F06-F08 and current CLI helpers before changing code. Work only tools/processforge.py, new tools/smoke_cli_audit_f0608.py and your private report/temp scope. Preserve committed F01-F05/docs fixes. No other workers, commits, installed infrastructure operations or lifecycle YAML edits.
Implement smallest compatible fixes for: registry_file_lock must never steal a live owner solely by mtime and release only its own ownership; active_organized_project_sessions calls undefined load_json; normalized_orchestrator_plan calls undefined default_expected_report_artifact. Reuse existing JSON/path conventions. Examine callers and Git history. Use existing cross-platform OS locking helpers if appropriate; handle stale/dead and malformed legacy locks conservatively, no unlink races allowing two writers.
Regression must exercise real processes for live old lock contention and reacquisition after owner death, exception cleanup and foreign ownership preservation; test empty/offline/active organized/corrupt presence and public workplace-mode disabling; public orchestrator plan normalization omitting report must agree with materialized task default. Capture initial failures then PASS. Register new smoke in release list in owned CLI. Do not change unrelated default behavior, refactor broad layers or invent PASS when sandbox prevents subprocess/temp operations; report limitation and give reproducible primary command. No forced sandbox workarounds.
Write report with design, files, commands/results, residual risks. Primary will review code and execute acceptance independently. Serena has no configured language; bounded shell/AST fallback accepted. Use gpt-5.6-luna/high, no subagents.
''')
(base/'f0608-review-brief.md').write_text('''# Independent F06-F08 review
After implementation and primary checks, review diff against 5c95391, audit findings and acceptance evidence. Write only your report. Examine lock ownership/races/dead-owner recovery and backwards compatibility of public CLI default/JSON behavior. Check tests reproduce original defects and exercise real public paths. Cite concrete defects or bounded PASS, distinguish tests you run from supplied evidence. No source edits, infrastructure operations or subagents.
''')
(base/'plan.md').write_text('''# Authorized delivery and continuation
Source baseline 5c95391 published to origin/dev and verified equal. Public changes only committed; local PF history remains preserved.
1. F06-F08 one junior PF shell implementation writer, primary acceptance, independent reviewer.
2. Primary prepares clean committed candidate, archive verification/extracted tests, inspects installed manifest and readonly update plan, applies user-authorized update with backups, then checks installed CLI/Workplace and local MCP operation. No force overwrite.
3. Preserve audit history and raw evidence; record partial/full release boundaries honestly. Runtime baseline startup failure requires diagnosis before claiming full release PASS.
4. Close current governed run only when remediation and local-update checks are recorded. F09-F12 are subsequent backlog.
''')
for name,data in [('intake-evidence.json',[{'kind':'artifact','artifact_id':'run-record','status':'ready','path':str(base/'plan.md')},{'kind':'gate','gate_id':'run-has-context','status':'passed','summary':'Source CLI context fresh; immutable capsule inspected, source published and remote equal.'}])]:
    (base/name).write_text(json.dumps(data,indent=2))
Path('.pf/logs/publish-f06-f08-20260910.md').write_text('''# Orchestrator log
## 2026-09-10 - primary
Task: user-authorized dev publication, F06-F08 repair and installed update.
Files: 34 public source/doc/test files committed as 5c95391; PF history preserved locally.
Checks: checksum, schema, public cleanliness, staged diff PASS; remote dev equals HEAD. Removed trailing blank line in new smoke only, regenerated checksums.
Tools: gh/git, source PF CLI. Connected MCP stale versus CLI fresh; Serena no active languages, bounded fallback.
Handoff: f0608-cli owns CLI and new smoke; primary owns candidate/update and acceptance. Review follows implementation.
Next: materialize shell plan and run worker, verify clean archive and update plan.
''')
