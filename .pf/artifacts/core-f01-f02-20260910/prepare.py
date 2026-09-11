"""Create private, bounded PF orchestration inputs and preserve dirty baseline."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
REL = OUT.relative_to(ROOT).as_posix()
CARRIER = 'garage-remediate-python-core-audit-f01-project-search-authorization-and'
RUN = 'core-f01-f02-shell-20260910'

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
save('baseline.json', {
    'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
    'status': subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).decode(),
    'sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in tracked if p and (ROOT/p).is_file()},
})
(OUT/'baseline.diff').write_bytes(subprocess.check_output(['git','diff','--binary'], cwd=ROOT))

common = '''Read your assignment and immutable capsule and this brief first. You are a bounded PF shell worker, not the primary orchestrator. Do not start new Work, change lifecycle states, refresh context, run other workers, install/restart/repair infrastructure, commit, publish, or edit files outside your allowed_files. Do not edit checksums, VERSION, previous audit evidence or tools/processforge.py. Existing dirty work belongs to other completed tasks: preserve it. All repository-local scratch belongs under your own .pf/tmp/core-f01-f02-20260910/<worker-id>/; system TemporaryDirectory fixtures are also allowed. Do not create scratch at repository root. Installed D:/ .agents Core/Workplace must never be updated by tests; use temporary fixtures only.

Serena was tried by primary and cannot extract symbols (Active languages: []); use bounded file reads/AST/search as fallback. This is a Python-only project with no selected platform/toolchain contract. Follow existing public smoke conventions and standard library/PyYAML already in requirements. No new dependencies. Avoid web research for this local defect task.

Keep an append-only work log in your owned evidence directory with current timestamp, files, checks, decisions and residual risks. Your final Markdown report must identify exact changes, baseline reproduction, Git-history origin, actual commands/exit/results, and limits. Save raw test outputs in your own evidence directory. Never claim a test passed from code inspection. On scope conflict stop edits and report the exact need. Implement minimal repairs with regression coverage; no broad refactor. Finish the report and exit; the primary agent reviews and collects your result.
'''

search = '''# F01: project authorization on shared Workplace search

Objective: repair the concrete F01 in .pf/artifacts/python-core-audit-20260908/report.md while keeping shared Workplace index ownership. Relevant source: ResourceSearchService.search in src/processforge_core/garage.py; ResourceSearchIndex/search/authorized_roots in local_resource_search.py; workplace_search_runtime_snapshot and context refresh in tools/processforge.py. Read the existing audit integration reproduction, but do not execute it directly (it overwrites preserved audit outputs).

Architecture decision: maintenance/status continue using the Workplace snapshot and physical shared index. Execute the query using the project's resolved authorization snapshot and project root. Do not filter a page of unrestricted results after querying: totals and pagination must also be authorized. Do not rebuild the shared index from a narrow project snapshot. Leave ResourceResolveService semantics unchanged. Avoid unrelated readiness/API changes.

Owned files: garage.py, tools/smoke_garage_cross_project_security.py, tools/smoke_garage_no_hooks_sessionless.py, tools/garage_search_smoke_support.py (optional new reusable fixture helper), and your evidence directory. No edits to local_resource_search.py or tools/processforge.py.

Reproduce original failure using registered packages in a real temporary Workplace, normal project manifest selection and context refresh, actual stdio MCP. Correct the existing two smoke fixtures to register resources through the current Workplace contract instead of hand-writing only project snapshots. Do not manually forge refreshed snapshots. The cross-project test currently passes vacuously with an empty shared index: require a positive control that the forbidden document IS indexed and is searchable through its authorized project/Workplace.

Acceptance: at least two projects/resources and distinct needles; own resource returns correct result, cross-project resource returns total=0 and no results via sessionless pf.search, pf.resolve denies it, session/project mismatch remains denied; test authorized page/total/offset with a common needle across projects and more than one allowed hit. Empty project authorization exposes no resources. Query A must not prune B from shared index; B remains searchable afterward. Sessionless/no-hooks/no-daemon test must retain its original assertions and yield one real authorized hit. Use original source copy or mutation in an isolated temporary copy to demonstrate regression FAIL before fix and PASS after, without reverting shared live files. Run the two modified smokes plus smoke_project_resource_narrowing_search.py if available. Public tests must not depend on .pf private artifacts.
'''

update = '''# F02: block unowned paths added by a Core archive

Objective: repair F02 in .pf/artifacts/python-core-audit-20260908/report.md. Relevant code: build_plan, ensure_inside, apply_update, atomic_write, rollback_update in src/processforge_core/core_update.py; existing tools/smoke_core_update_manifest.py provides isolated archive fixture helpers. Read audit reproduce_fast.py for the unowned collision example, but do not execute it directly or rewrite old audit output.

Architecture decision: a target newly added to Core ownership must be absent. If it collides with an existing unowned object, return an explicit plan blocker with its path, and apply must refuse before mutations. force_local_modifications only covers already-owned modified files and must never bypass this new blocker. Do not silently adopt even identical bytes. Handle existing regular files, directories and detectable symlinks/broken symlinks without losing objects; consider non-directory ancestors of a new target. Keep new policy operationally bounded; no new adoption API, broad updater redesign, or incidental F09 repair.

Owned files: src/processforge_core/core_update.py, tools/smoke_core_update_manifest.py, and your evidence directory. No docs/schema/CLI/checksum edits. Prefer adding regressions to existing registered smoke so public release suite executes them.

Acceptance: real temporary old Core + valid new archive newly claims a user file; plan has blocker, apply(confirm=True) refuses, user bytes/old manifest/other owned bytes unchanged, no update or backup state created; same refusal with force_local_modifications=True; same-byte collision also refused; directory collision refused; newly added child under an unowned regular-file ancestor refused rather than partial update. Late collision created after a prior successful plan is detected when apply rebuilds the plan. Existing owned-file force/rollback behavior remains passing; clean absent added paths still install/rollback successfully. Test symlinks where privileges support them and explicitly record skip otherwise, never fabricate Windows support. Retain existing full smoke cases. Prove new regression fails against baseline core_update.py in an isolated copy and passes after repair; no live shared-source reverting.
'''

assurance = '''# Independent regression acceptance after implementation

Start only after both implementation reports exist and the primary confirms their terminal exits. You own only your evidence directory/report, not source. Read plan and reports and inspect actual source diff against baseline.diff. Run both changed search smokes, existing project resource narrowing, and full core update manifest smoke. Independently verify positive controls and that tests are portable without private .pf imports. Check original baseline versions using isolated public copy/mutation if implementation evidence does not convincingly prove the new assertions fail before repair. Test user-file preservation and force refusal plus allowed/denied search, totals and persistent shared index. Do not run the long full release suite; the primary owns it after all source edits/checksums. Deliver actual commands, results and any gaps; do not infer pass from exit alone or fix product files.
'''

review = '''# Independent post-implementation code review

Start only after implementation and test-assurance are accepted. Report-only scope. Inspect actual diff from baseline, both worker reports, assurance evidence, source and test semantics. Focus on authorization at SQL/count/pagination boundary, using project root for relative resource roots while maintaining whole Workplace index, and unowned collision policy before side effects (including force, directories, dangling symlinks, ancestor files). Confirm original dirty required-output/docs changes are preserved. Identify concrete actionable findings with file/line, trigger, impact, and suggested minimal fix; do not add theoretical unrelated audit scope. State no findings if appropriate and list actual checks versus inspection. Do not change source or lifecycle.
'''

workers=[]
specs=[
 ('f01-search',search,['src/processforge_core/garage.py','tools/smoke_garage_cross_project_security.py','tools/smoke_garage_no_hooks_sessionless.py','tools/garage_search_smoke_support.py'],[],True,'implementation','high'),
 ('f02-update',update,['src/processforge_core/core_update.py','tools/smoke_core_update_manifest.py'],[],True,'implementation','high'),
 ('f0102-assurance',assurance,[],['f01-search','f02-update'],False,'assurance','medium'),
 ('f0102-review',review,[],['f0102-assurance'],False,'assurance','high'),
]
for wid, brief, files, deps, writer, mode, effort in specs:
    evidence=f'{REL}/{wid}'
    (ROOT/evidence).mkdir(parents=True,exist_ok=True)
    report=f'{evidence}/report.md'
    brief_path=f'{REL}/{wid}-brief.md'
    (ROOT/brief_path).write_text(brief+'\n'+common,encoding='utf-8')
    workers.append(dict(id=wid,title=brief.splitlines()[0].lstrip('# '),role='worker' if writer else 'reviewer',process='task-batch-execution',objective=f'Execute bounded brief {brief_path}',execution_mode=mode,writer=writer,model='gpt-5.6-luna',reasoning_effort=effort,allowed_files=files+[evidence+'/**',f'.pf/tmp/core-f01-f02-20260910/{wid}/**'],allowed_read_files=['src/**','tools/**','docs/**','templates/**','schemas/**','requirements.txt','.pf/contexts/project-context.snapshot.yaml','.pf/artifacts/python-core-audit-20260908/**',REL+'/**'],forbidden_files=['VERSION','CHANGELOG.md','checksums/**','tools/processforge.py','.pf/process-forge.yaml','.pf/artifacts/python-core-audit-20260908/**'],required_sources=[brief_path],required_outputs=[dict(id=wid+'-report',path=report,type='markdown',required=True)],expected_report_artifact=report,runtime_driver='codex-exec',depends_on=deps,allow_subagents=False,worker_may_rebuild_context=False))
save('orchestrator-plan.yaml',dict(schema_version=1,run=dict(id=RUN,title='F01/F02 correctness remediation with bounded junior shell workers',process='multi-agent-task-orchestration'),orchestrator=dict(role='orchestrator',responsibilities=['design and disjoint ownership','review durable worker evidence','integration and final source validation','governed closure']),runtime=dict(default_driver='codex-exec',supervisor_profile='default',start_policy='manual',max_parallel_workers=2),workers=workers,integration=dict(required=True,role='orchestrator',expected_output=f'{REL}/integration-report.md'),metadata=dict(carrier_run=CARRIER,authorization='User explicitly requested junior PF shell workers; separate orchestration preserves carrier process pin. F01/F02 first bounded remediation batch; F03-F12 deferred.')))
(OUT/'plan.md').write_text('''# F01/F02 remediation plan — 2026-09-10

Status: planned. Primary orchestrator owns acceptance and lifecycle. User authorizes junior PF shell workers. Carrier is pinned task-batch; a separate specialized multi-agent-task-orchestration run owns shell assignments, without changing the pinned process.

1. Intake: preserve dirty source baseline; use audit F01/F02 evidence and current source.
2. Design: Workplace owns shared index maintenance; project snapshot authorizes query. Unowned added-path collisions block before update writes, including under force. No adoption feature.
3. Implementation: Luna/high F01 owns garage.py and two search smokes plus optional fixture helper; Luna/high F02 owns core_update.py and existing updater smoke. File scopes disjoint.
4. Assurance: after implementation exits, report-only Luna/medium runs independent targeted checks; report-only Luna/high reviews after assurance. Primary adjudicates findings and accepts actual source.
5. Integration: primary owns any release registration and public checksums, preserving pre-existing changes; source/schema/cleanliness checks and appropriate complete source suite. No version change, commit, publication, or installed Core update.
6. Delivery: durable reports, handoff, PF doctors and terminal lifecycle. Source PASS never substitutes archive/extracted release qualification.

F03-F12 remain follow-up work. The existing sessionless fixture blocker belongs in F01 because correct isolation tests require real Workplace registration. Source tests use temporary fixtures only.
''',encoding='utf-8')
save('intake-evidence.json',[dict(kind='artifact',artifact_id='run-record',status='ready',path=f'.pf/runs/{CARRIER}/run.yaml'),dict(kind='gate',gate_id='run-has-context',status='passed',summary='Fresh context, immutable carrier capsule read, existing dirty source baseline and bounded remediation plan recorded.')])
save('planning-evidence.json',[dict(kind='artifact',artifact_id='task-plan',status='ready',path=f'{REL}/plan.md'),dict(kind='gate',gate_id='tasks-defined',status='passed',summary='Two disjoint implementation workers followed by independent assurance and review; scopes and acceptance defined.')])
print(REL)
