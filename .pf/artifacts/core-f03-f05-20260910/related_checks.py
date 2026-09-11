from concurrent.futures import ThreadPoolExecutor
import json,sys
from check import execute,BASE
names=['smoke_work_transition_records_evidence','smoke_work_transition_recovers_after_invalid_evidence','smoke_work_transition_final_stage_completes_run','smoke_work_transition_emits_stage_events','smoke_work_transition_snapshot_pinned_process','smoke_work_transition_branching_if_supported','smoke_process_execution_integrity','smoke_process_execution_state_semantics','smoke_multi_process_work_capsule','smoke_process_run_task_batch']
def run(name):return name,execute('related-'+name,[sys.executable,'tools/'+name+'.py'])
with ThreadPoolExecutor(max_workers=2) as pool: results=dict(pool.map(run,names))
(BASE/'related-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
raise SystemExit(0 if not any(results.values()) else 1)
