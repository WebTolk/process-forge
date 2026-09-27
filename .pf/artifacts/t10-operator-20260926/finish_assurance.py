"""Retain initial results; rerun corrected/timing-sensitive checks only."""
import ast,importlib.util
from work import *
for name in ['runtime_metrics','runtime_monitor']:
    command(name+'-final',[sys.executable,'-B',ROOT/'tools'/('smoke_'+name+'.py')])
command('checksums-final',[sys.executable,'-B',ROOT/'tools/validate-process-forge-checksums.py','--check'])
command('diff-check',['git','diff','--check'])
baseline=json.loads((HERE/'baseline.json').read_text())
spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/validate-process-forge-checksums.py');inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
current={p.relative_to(ROOT).as_posix():p for p in inv.public_files(ROOT)+[ROOT/'checksums/processforge.sha256']}
changed={n for n,p in current.items() if n not in baseline['public_sha256'] or sha(p)!=baseline['public_sha256'][n]}
assert changed<=set(baseline['scope']) and not(set(baseline['public_sha256'])-set(current))
checks=['runtime_metrics-final','runtime_monitor-final','server_operator','diagnostics_configure','diagnostics','diagnostics_process_invariance','process_event_concurrency','runtime_singleton_orphan','runtime_status_version_truth','runtime_scheduler_failure_isolation','runtime_no_domain_file_patterns','docs_agent_no_manual_infra','docs_mcp_host_owned_stdio','docs_codex_hooks_optional','schemas','checksums-final','public-cleanliness','diff-check']
assert all(json.loads((HERE/(n+'.json')).read_text())['exit_code']==0 for n in checks)
original=json.loads((HERE/'implementation.json').read_text())
assert {n for n,p in current.items() if n not in original['source_sha256'] or sha(p)!=original['source_sha256'][n]}=={'tools/smoke_runtime_metrics.py','tools/pf_runtime/monitor.py','tools/smoke_runtime_monitor.py','checksums/processforge.sha256'}
save('assurance-results.json',dict(status='PASS',changed_files=sorted(changed),source_sha256={n:sha(p) for n,p in current.items()},checks=checks,initial_failures_preserved=['runtime_metrics.json','runtime_monitor.json'],correction=['assurance-correction.md','pid-probe-correction.md'],journal_ast_preserved=True))
(HERE/'assurance.md').write_text('# Assurance\n\nPASS: 18 focused checks including full actual checkout schema validation, T09 five-profile real Work lifecycle invariance, existing monitor terminal/no-write/probe cases, actual guarded HTTP worker/request/scheduler/admission/auth/owner cases, profile CLI plan/apply/lock/expiry, new metrics semantics/budgets/canonical dedup and real publisher-to-monitor projection, concurrent journal writers, Runtime singleton/status/scheduler isolation, docs boundaries, checksum/cleanliness/diff. Exact recorded commands/results: assurance-results.json.\n\nInitial fixture rounding and slow tasklist observations remain in original results. The fixture was corrected and the Windows PID observation now uses a nonblocking native process handle check, including actual live/exited PID and independent access-denied/failure tests. See assurance-correction.md and pid-probe-correction.md. Network timeouts remain unchanged. Review verified admission serialization before stop, independent metric budgets, no raw source identities in aggregate output, locked policy preservation and protected journal append AST. No unresolved source defect found.\n\nBrowser verification: not_applicable, local terminal and CLI only. Existing real terminal state-machine/resize/cleanup tests passed; no new browser UI. Native POSIX and connected host MCP acceptance are not claimed by Windows subprocess tests. Candidate/archive/update plan will be qualified before release.\n',encoding='utf-8')
print('PASS final assurance',flush=True)
