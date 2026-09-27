"""Adapt the proven private delivery helpers; retain official PF commands."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
previous=ROOT/'.pf/artifacts/t10-installed-delivery-20260926'
s=(previous/'build.py').read_text(encoding='utf-8')
s=s.replace("BASE='69110c50559d994d7a31e751b7cd7afc989698db'", "BASE='40c9894227738472976546849047550415099486'")
s=s.replace("OLD=ROOT/'.pf/tmp/t06-installed-delivery-20260926/candidate'", "OLD=ROOT/'.pf/tmp/t10-installed-delivery-20260926/candidate'")
s=s.replace("CANDIDATE=ROOT/'.pf/tmp/t10-installed-delivery-20260926/candidate'", "CANDIDATE=ROOT/'.pf/tmp/t10-operator-20260926/candidate'")
start=s.index('EXPECTED=');end=s.index("assert state(",start)
s=s[:start]+"EXPECTED=set(json.loads((HERE/'assurance-results.json').read_text())['changed_files']) | {'tools/processforge.py','tools/smoke_process_event_concurrency.py','docs/concepts/session-telemetry.md','docs/ru/concepts/session-telemetry.md','checksums/processforge.sha256'}\n"+s[end:]
s=s.replace("['stage']['id']=='implementation'", "['stage']['id']=='code-assurance'")
s=s.replace("ROOT/'.pf/artifacts/t10-monitor-20260926/assurance-results.json'", "HERE/'assurance-results.json'")
s=s.replace("save('baseline.json',result)", "save('delivery-baseline.json',result)")
s=s.replace("Deliver the read-only terminal Runtime monitor", "Deliver bounded operator metrics, guarded server controls and journal serialization")
s=s.replace("['runtime_monitor','runtime_singleton_orphan','runtime_status_version_truth','runtime_scheduler_failure_isolation','runtime_no_domain_file_patterns','docs_agent_no_manual_infra','docs_mcp_host_owned_stdio','docs_codex_hooks_optional']", "['runtime_metrics','server_operator','diagnostics_configure','process_event_concurrency']")
s=s.replace("processforge-1.1.0-t10-", "processforge-1.1.0-operator-")
s=s.replace("command('extracted-monitor',[sys.executable,'-B',EXTRACTED/'tools/smoke_runtime_monitor.py'],cwd=EXTRACTED)", "for name in ['runtime_metrics','server_operator','diagnostics_configure','runtime_monitor','process_event_concurrency']:\n    command('extracted-'+name,[sys.executable,'-B',EXTRACTED/'tools'/('smoke_'+name+'.py')],cwd=EXTRACTED)")
(HERE/'build.py').write_text(s,encoding='utf-8')
s=(previous/'install.py').read_text(encoding='utf-8')
s=s.replace("ROOT/'.pf/tmp/t10-installed-delivery-20260926/extracted'", "ROOT/'.pf/tmp/t10-operator-20260926/extracted'")
s=s.replace("['runtime_monitor','runtime_status_version_truth','runtime_singleton_orphan']", "['runtime_metrics','server_operator','diagnostics_configure','process_event_concurrency']")
s=s.replace("assert monitor['kind']=='pf.runtime.monitor'", "assert monitor['kind']=='pf.runtime.monitor'\noperator=json.loads(command('installed-server-status',cli('server','status','--workplace',WP,'--json')))\nassert operator['metrics'] is not None, operator['issues']\nresult['live_metrics']=operator['metrics']")
(HERE/'install.py').write_text(s,encoding='utf-8')
(HERE/'activity.py').write_bytes((previous/'activity.py').read_bytes())
print('Prepared official updater delivery helpers')
