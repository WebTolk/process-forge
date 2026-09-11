import json
from pathlib import Path
base=Path('.pf/artifacts/core-f09-f12-20260910')
base.mkdir(parents=True,exist_ok=True)
run='garage-remediate-python-core-audit-f09-f12-updater-search-and-raw-ingres'
old=json.loads(Path('.pf/artifacts/publish-f06-f08-20260910/orchestrator-plan.yaml').read_text())
old['run']={'id':'core-f09-f12-shell-20260910','title':'F09-F12 update integrity search and incremental ingress','process':'multi-agent-task-orchestration'}
old['runtime']['max_parallel_workers']=3
common='''Work only your allowed source/test files and private report/temp directory. No commits, installed infrastructure actions, lifecycle YAML edits, additional workers, or unrelated refactors. Preserve F01-F08. Use bounded source reads and Git history; Serena has no active languages, shell/AST fallback accepted. Do not dump tools/processforge.py or broad diffs. If tests hit sandbox PermissionError, stop that test immediately, do not investigate ACL/environment or retry variants; record exact failure and primary command. Primary owns real acceptance. Write report with design, files, command results, limitations. Finish once bounded task/report is ready.\n'''
specs=[
('f09-update',['src/processforge_core/core_update.py','tools/smoke_core_update_missing_owned.py'],'medium', '''F09: build_plan records missing owned unchanged file, but apply falsely reports success without restoring it. Implement manifest-backed restoration of missing files still present in new manifest, preserving added/changed/removed semantics. Include writes in journal and rollback bookkeeping (prior absence must restore as absence). Read core_update build_plan/apply_update/rollback/repair and smoke_core_update_manifest helpers. Do not broaden update policy for intentional local modifications; do not overwrite unknown/user files, parent file collisions or nonregular owned paths. Plan must remain read-only. Regression: absent unchanged restored with exact hash; missing changed and removed; unrelated user file preserved; rollback restores prior absence; injected failure leaves recoverable progress. New standalone smoke with --root argument matching existing style.\n'''),
('f1011-search',['src/processforge_core/local_resource_search.py','tools/smoke_search_source_integrity.py'],'medium', '''F10/F11: overlapping sources yield duplicate logical docs; INSERT OR REPLACE changes rowid and strands FTS records, so count/pagination wrong. Deduplicate by resource identity + relative path before write, keep generation/count and FTS coherent, normal refresh must repair prior duplicate index state. Explicit-file branch ignores include/exclude; apply same matching as directory branch for explicit files and file-root resource, preserving allowed files and scoped authorization. Read _documents/_iter_source_files/build_index/status/query and relevant existing search smokes. New standalone --root smoke: directory plus explicit overlap and repeated patterns, exactly one document/FTS row and correct pages/total; refresh legacy inconsistent state; excluded explicit content absent, include mismatch absent, file-root allow/exclude; legitimate search unaffected, distinct resources remain distinct.\n'''),
('f12-ingress',['tools/pf_runtime/raw_ingress_kernel.py','tools/smoke_raw_ingress_incremental_recovery.py'],'high', '''F12: ingest invokes full raw history scan for every new lookup miss, including no stable native ID. 20 events decode 190 historical records. Design a bounded durable recovery checkpoint/tail strategy under existing global lock before implementation: normal new events must not decode old history repeatedly; recover raw-before-index failures including failure between raw and native indexes. Preserve existing missing-index crash recovery tests, dedup/native conflict quarantine, concurrency, restart and legacy journal migration. Never merely skip recovery on misses; need evidence distinguishing new events from unindexed durable raw. Avoid accumulating/re-writing a full event ID list each ingest (still quadratic). A compact durable recovery catalogue/checkpoint with indexed lookups is acceptable if needed; keep dependencies stdlib. Do not redesign lock ownership. Fail safely on truncated/corrupt journals. Standalone --root smoke counts actual historical record decodes/bytes (not fragile timings), covers 20 and 100 new events with and without native IDs, restart, append-before-index crash, partial index write crash, legacy journal, corruption and concurrency. Document any maintenance limitations.\n'''),
('f0912-review',[],'medium', '''Independent report-only review after all implementations and primary acceptance. Review only diff in the six assigned source/test files versus 52774e4 and integration acceptance report. Seek concrete updater rollback/unknown-file issues, search authorization/exclusion/count errors, ingress crash recovery/performance/dedup races. Do not read whole CLI or broad runtime. Distinguish own checks from supplied evidence. At most one focused smoke attempt per area; on permission error report immediately, no environment exploration. Finish with actionable findings or bounded PASS.\n''')]
workers=[]
for wid,owned,effort,brief in specs:
 review=not owned
 w=dict(old['workers'][1 if review else 0])
 w.update(id=wid,title=wid,objective=f'Execute bounded brief {base.as_posix()}/{wid}-brief.md',model='gpt-5.6-luna',reasoning_effort=effort,depends_on=['f09-update','f1011-search','f12-ingress'] if review else [])
 w['allowed_files']=owned+[f'{base.as_posix()}/{wid}/**',f'.pf/tmp/{wid}/**']
 w['allowed_read_files']=['src/processforge_core/core_update.py','src/processforge_core/local_resource_search.py','tools/pf_runtime/raw_ingress_kernel.py','tools/smoke_*.py','docs/**','.pf/artifacts/python-core-audit-20260908/**',f'{base.as_posix()}/**']
 w['forbidden_files']=['VERSION','CHANGELOG.md','checksums/**','tools/processforge.py','.pf/process-forge.yaml','.pf/artifacts/python-core-audit-20260908/**']
 w['required_sources']=[f'{base.as_posix()}/{wid}-brief.md']
 report=f'{base.as_posix()}/{wid}/report.md'
 w['required_outputs']=[{'id':wid+'-report','path':report,'type':'markdown','required':True}]
 w['expected_report_artifact']=report
 workers.append(w)
 (base/f'{wid}-brief.md').write_text('# '+wid+'\n'+common+brief)
old['workers']=workers
old['integration']['expected_output']=f'{base.as_posix()}/integration-report.md'
old['metadata']={'carrier_run':run,'authorization':'User authorized junior PF shell workers, dev publication and installed Core update/testing; primary owns delivery and acceptance.'}
(base/'orchestrator-plan.yaml').write_text(json.dumps(old,indent=2)+'\n')
(base/'plan.md').write_text('''# F09-F12 authorized continuation
Baseline dev/source/installed: 52774e4761975ce0cb29095081c5294db882007d. Source CLI context fresh, connected MCP stale; CLI authoritative for this run.
Architecture: restore manifest-owned missing files through existing update journal; deduplicate logical search documents and honor source filters consistently; ingress uses durable incremental recovery preserving raw-before-index contract.
Ownership: f09-update owns core_update and new updater smoke; f1011-search owns local_resource_search and new search smoke; f12-ingress owns raw_ingress_kernel and new recovery smoke. Review starts only after implementation and primary tests. Primary owns release registration, checksums, delivery, acceptance, governance.
Acceptance: reproduce baseline F09-F12, focused regression/related tests, independent review, commit/push dev then exact clean candidate archive and extracted quick test, inspect and apply user-authorized update, installed regressions and Workplace preservation, Runtime restart only after workers/jobs drain, verified remote/source/installed commit equality. Full release qualification remains distinct from focused PASS; intermittent Runtime fixture startup remains known backlog.
Historical approved audit and unrelated dirty PF files remain preserved. No GitHub comments or public release planned.
''')
for name,artifact,gate in [('intake','run-record','run-has-context'),('planning','task-index','run-has-tasks')]:
 path='plan.md' if name=='intake' else 'orchestrator-plan.yaml'
 (base/f'{name}-evidence.json').write_text(json.dumps([{'kind':'artifact','artifact_id':artifact,'status':'ready','path':f'{base.as_posix()}/{path}'},{'kind':'gate','gate_id':gate,'status':'passed','summary':'Bounded architecture and disjoint assignments documented; source context fresh.'}],indent=2))
Path('.pf/logs/core-f09-f12-20260910.md').write_text('''# Orchestrator log
## 2026-09-10 11:30 UTC - primary
Task: Continue F09-F12 remediation and authorized dev/local delivery.
Files analyzed: three audited modules and original audit; current assignment/capsule.
Artifacts: plan, four bounded worker briefs, shell plan. Templates: previous accepted PF shell orchestration.
Tools: source CLI, Git, bounded shell. Serena symbol extraction unavailable (Active languages empty); connected MCP snapshot stale, source CLI fresh.
Decision: three non-overlapping junior PF shell workers; review after implementation/acceptance. Primary retains delivery and lifecycle ownership.
Risks: ingress crash recovery and updater rollback require real fault injection; full suite Runtime startup intermittent baseline unresolved.
Next: materialize shell assignments, launch workers, capture original failures independently.
Handoff: file ownership explicit in plan; no workers may edit CLI/checksums or historical audit.
''')
print(base)
