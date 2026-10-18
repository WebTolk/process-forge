# Runtime restart and CPU observation

## 2026-10-17 - Codex / operator

Task: explicit user request to restart pf-app-server and measure CPU. Scope is existing service lifecycle and read-only observations, with private artifacts; product writes and subagents forbidden.
Files analyzed: installed owner state, installed/source VERSION and module hashes, current Runtime lifecycle functions, runtime-autostart documentation.
Status: owner PID 13540 verified; 30-second baseline sampling started. Installed code remains pre-SQLite.
Tools: PF context/start/state, Serena, Windows process queries, operation-local CPU sampling helper.
Follow-up: guarded restart, new owner verification, startup/settled CPU measurements, exact results. General 1.2.0 acceptance remains deferred.

## 2026-10-17 - Codex / operator: guarded refusal

Task: requested restart and CPU comparison. Files changed: private report, baseline CPU and service/worker observation artifacts; no product edits.
Status: baseline owner CPU 21.8876% average over 30 seconds on 4 logical processors. Two normal server restart calls rejected with HTTP 409 runtime_busy_or_activity_unknown. Old owner remains PID 13540; no restart or post-restart measurement claimed.
Evidence: before-cpu.json, before-status.json, restart-command.txt, restart-retry-command.txt, shutdown-worker-observation.json, extended-worker-observation.json, restart-refusal.md, report.md.
Decision: do not silently bypass the guard or infer zero from partial coverage. Specific --force operator approval requested asynchronously; dependent action waits for reply. Same exact Work remains in progress at implementation, not complete or cancelled.
Risk/follow-up: installed modules still precede SQLite source; after an authorized restart, verify new owner then measure startup and settled CPU. Core update, journal migration, MCP restart and general 1.2.0 acceptance remain outside this operator scope.

## 2026-10-17 06:18 UTC - Codex / operator: explicit force approval

Task: continue the same exact operator Work after the user explicitly permitted the requested server restart --force.
Files changed: force-authorization.md; this append-only log. No capsule or product change.
Status: fresh context and exact assignment/capsule rechecked; managed one-service restart is authorized. Previous no-force plan condition is superseded only by this explicit user answer.
Follow-up: verify old owner, execute installed managed restart, verify new owner and readiness, measure initial 30-second and settled 60-second CPU windows. Preserve the existing installed-code/device-acceptance boundary.

## 2026-10-17 06:20 UTC - Codex / operator: restart and measurements complete

Task: explicitly approved installed server restart --force and CPU comparison. Files changed: private report, restart result, new-owner/after-state and interval sampling artifacts; no product writes.
Status: managed command exit 0; old owner/launcher exited; new PID 16976, new instance, readyz=true. CPU before 21.8876% / 30 s; first measured post-start window 21.4189% / 30 s; following settled window 20.7354% / 60 s, max 26.9430%. Connected MCP PID 5284 remains unchanged and consumed 0% during both post-start windows.
Tools: installed operator CLI, Windows process identity/GetProcessTimes, local readiness, fixed-duration pinned-handle measurements. No additional synthetic workload or PF control calls during the 60-second sample.
Decision: requested restart and measurement achieved; restart did not remove sustained CPU consumption. Installed code remains the previous 1.2.0 without source SQLite changes. Health remains degraded with recorded scheduler failures, reported honestly and not repaired here.
Follow-up: retain operational evidence, complete the exact Work and deliver only owned records. Core update/migration and general 1.2.0 acceptance remain separate.

## 2026-10-17 06:23 UTC - Codex / operator: assurance and closeout

Task: verify and retain completed restart/CPU observation. Files changed: assurance.md, delivery.md, evolve.md, after-processes.json, cpu-summary.json and retained measurement helper; no product files.
Status: actual process replacement/readiness and interval arithmetic passed. Operational objective complete; terminal Work closeout and owned-record publication follow. Source/product release profile skipped explicitly because this is an operator-only task.
Risks: ready/degraded service; unchanged previous installed code; sustained CPU remains. No SQLite device migration or connected-MCP/1.2.0 acceptance was performed.
Handoff: final report supplies 21.8876% before, 20.7354% after, PID 13540 -> 16976 and raw evidence. Further update/migration requires its own operator scope, not a repeated restart.
