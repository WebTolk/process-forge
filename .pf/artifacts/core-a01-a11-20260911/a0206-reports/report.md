# Primary fallback: A02/A06

Author: primary orchestrator. The assigned shell worker failed with backend 403
before editing product files; its original failed status and logs are preserved
under worker-failures/wave2/a0206-reports. This is not a successful worker report.

Implemented one project-output resolver used before required-output checks,
worker command construction, collection and host report authorization. Absolute,
traversal, drive-relative and canonically escaping paths are rejected before
file reads. Authenticated PF-owned reports retain diagnostic path text in the
private transcript after exact file, task, attempt, session, native-id, content,
hash and provenance checks. Secret and untrusted-host content checks remain.

Primary verification PASS: smoke_expected_report_containment,
smoke_authenticated_report_content, smoke_conversation_completeness,
smoke_process_run_task_batch. New regressions fail the audited baseline and pass
source. Real symlink creation is unavailable on this Windows account; canonical
resolution is checked in code and traversal/absolute cases ran with read guards.

Changed: tools/processforge.py, tools/pf_runtime/host.py, two new smoke scripts.
Independent source review is in progress under review-mcp-reports.
