from pathlib import Path
import json

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
REL=OUT.relative_to(ROOT).as_posix()
base=json.loads((OUT/'wave1-plan.yaml').read_text())
base['run']={'id':'core-a01-a11-review-20260911','title':'Independent A01-A11 remediation review','process':'multi-agent-task-orchestration'}
base['runtime']['max_parallel_workers']=2
template=base['workers'][0]
base['workers']=[]
specs=[
 ('review-runtime-core',['src/processforge_core/local_resource_search.py','src/processforge_core/core_update.py','tools/pf_runtime/service.py','tools/smoke_runtime_scheduler_failure_isolation.py','tools/smoke_runtime_singleton_orphan.py','tools/smoke_search_file_root_containment.py','tools/smoke_core_update_migration_sources.py','tools/smoke_long_lived_runtime.py'], 'Review completed A01 A03 A04 A05 A10 source changes, including primary integration. Focus actual correctness, real failure isolation and health recovery/liveness, live orphan/missing lock ownership and same guard across cleanup/acquire/release, dead recovery, search canonical containment and old-index invalidation, migration source preflight and structured failure with durable partial migration backup records. Original suite PID-reuse fixture was intentionally corrected: a live PID without verifiable identity is no longer sufficient evidence for takeover; recovery after PID exit remains tested. Inspect targeted diff and provided verification logs. Find concrete defects or state pass with precise limitations. Do not ask to restore unsafe old behavior solely for compatibility.'),
 ('review-mcp-reports',['tools/processforge.py','tools/pf_runtime/host.py','tools/pf_runtime/mcp_server.py','tools/pf_runtime/session_read.py','tools/pf_runtime/codex_hooks.py','tools/smoke_expected_report_containment.py','tools/smoke_authenticated_report_content.py','tools/smoke_mcp_jsonrpc_validation.py','tools/smoke_classifier_distribution_parity.py','tools/smoke_session_identity_roundtrip.py','tools/smoke_codex_lifecycle_identity.py'], 'Review completed A02 A06 A07 A08 A09 A11 changes only. Main will launch after A07/A11 implementation ends. Focus report path resolution before reads/writes, narrow path-text exemption with secret/hash/provenance/session guards and raw retry idempotence; JSONRPC validation vs business errors and notification silence; opaque exact session IDs plus collision/legacy behavior; stable classifier provenance without hiding actual stale changes; distinct lifecycle facts with stable retries. Do not expand into unrelated CLI audit. Initial reports A02/A08 workers failed backend403; their source repairs are primary-authored and require independent review just as others. Read exact changed functions via git diff, no whole-CLI dump.'),
]
for task,files,detail in specs:
    (OUT/task).mkdir(exist_ok=True)
    brief=f'{REL}/{task}-brief.md'
    (ROOT/brief).write_text('Independent read-only reviewer. No source edits, no infrastructure/lifecycle commands, no subagents, no commits. Keep review bounded: at most 16 focused calls; reads <=180 lines; NEVER dump tools/processforge.py or whole .pf. Serena unavailable (no languages); use targeted diff/rg/AST. Prefer substantive findings over style. On first sandbox PermissionError stop test environment workarounds and report exact runnable reproduction for primary. You may save a small reproduction only under your artifact folder. Report <=100 lines, severity/file/line/scenario/acceptance for each real finding; separate hypotheses/unverified from proven. Write report even if blocked. Use relative paths in report.\n\n'+detail+'\n\nGoverning design: '+REL+'/design.md. Primary logs: .pf/logs/core-a01-a11-20260911.md. Validation evidence: '+REL+'/validation/.\n',encoding='utf-8')
    worker=json.loads(json.dumps(template))
    worker.update(id=task,title=task,role='reviewer',writer=False,execution_mode='assurance',objective=f'Independent review per {brief}',allowed_files=[f'{REL}/{task}/**',f'.pf/tmp/{task}/**'],allowed_read_files=files+['tools/smoke_domain_neutral_core_helpers.py','tools/processforge_subprocess.py','docs/concepts/**',f'{REL}/**','.pf/logs/core-a01-a11-20260911.md','.pf/AGENTS.md'],required_sources=[brief,f'{REL}/design.md'],required_outputs=[{'id':task+'-report','path':f'{REL}/{task}/report.md','type':'markdown','required':True}],expected_report_artifact=f'{REL}/{task}/report.md')
    base['workers'].append(worker)
(OUT/'review-plan.yaml').write_text(json.dumps(base,indent=2),encoding='utf-8')
print('Prepared bounded independent reviewers')
