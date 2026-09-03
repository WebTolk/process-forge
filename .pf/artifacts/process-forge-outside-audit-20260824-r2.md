# ProcessForge Outside Audit - Repeat 2 - 2026-08-24

Target project: `D:\Dev\wt-read-in-ai`.

Report path: `D:\Dev\process-forge\.pf\artifacts\process-forge-outside-audit-20260824-r2.md`.

Timeline path: `D:\Dev\process-forge\.pf\artifacts\process-forge-session-timeline-20260824-r2.csv`.

Audit time: `2026-08-24T11:49:24+04:00` and following commands in the same turn.

Auditor mode: outside auditor, read-only against the target project except for writing this separate report and timeline in the ProcessForge repository artifacts directory.

## Executive Summary

Verdict: the original work on `D:\Dev\wt-read-in-ai` was not captured as a first-class Codex-session-to-ProcessForge chain. The repeat audit again found no raw ingress rows and no Agent Ledger routing for the inferred original Codex session ids `01a03241-9d12-7ea3-953c-f52b3a241319` and `01a03250-70fd-71e2-bbf8-4e981c0ab9bb`.

A later, manually bootstrapped PF-native session exists: `codex-20260824-inside-audit`, run `run-process-forge-inside-audit-20260824`, task `task-process-forge-inside-audit-20260824`. That run is real and completed, and `run-doctor --runtime-events` passes. It does not prove that the original Codex session was captured by hooks or routed by Ledger.

Main confirmed defects:

- `DEFECT-PF-001`: target Codex session ids are absent from raw ingress, Agent Ledger, current-sessions, and presence.
- `DEFECT-PF-002`: ProcessForge MCP rejects the original Codex id as `unknown_session` / not routed by Agent Ledger.
- `DEFECT-PF-003`: target project context snapshot is stale and `pf.search`/resource `pf.resolve` are blocked by `snapshot_not_fresh`.
- `DEFECT-PF-004`: execution readiness is blocked by missing registry declarations for `filesystem.read` and `filesystem.write`.
- `DEFECT-PF-005`: Codex chat content is not captured; hook outbox payloads are metadata-only.
- `DEFECT-PF-006`: `current-sessions\wt-read-in-ai.json` still says `online` for `codex-20260824-inside-audit`, while presence and Ledger say the session expired/stale.

False positive / misleading diagnostic:

- `doctor-project` says `.gitignore missing .pf/process-forge.local.yaml`, but `git check-ignore -v` proves `.gitignore:1:.pf/` ignores it. This is a policy-specific exact-pattern diagnostic, not a public-exposure risk in this repository state.

## Environment

Evidence command:

```powershell
Get-Date -Format o; hostname; (Get-CimInstance Win32_OperatingSystem).Caption; (Get-CimInstance Win32_OperatingSystem).Version; python --version; codex --version
```

Result:

- Time: `2026-08-24T11:49:24.1165032+04:00`
- Host: `WebTolkNB`
- OS: `Microsoft Windows 11 Home`, `10.0.26200`
- Python: `3.14.3`
- Codex CLI: `0.149.1`

Target Git / PF version evidence:

```powershell
git status --short --branch
git log --oneline --decorate --max-count=3
python .pf\runtime\bin\pf.py version
```

Result:

- Git: `## main...origin/main`
- HEAD: `4061af0 (HEAD -> main, origin/main) Document root plugin packaging`
- Previous: `65989ec Initial Joomla content plugin`
- ProcessForge: `1.1.0`, Spec `1.0`, Schema bundle `1.0`

## Correlation Keys

Primary inferred target Codex session:

- `01a03241-9d12-7ea3-953c-f52b3a241319`
- Source: `C:\Users\musst\.codex\sessions\2026\08\24\rollout-2026-08-24T09-32-36-01a03241-9d12-7ea3-953c-f52b3a241319.jsonl:1`
- Result: session metadata has `cwd` = `D:\Dev\wt-read-in-ai`.

Secondary diagnostic/outside-audit Codex session:

- `01a03250-70fd-71e2-bbf8-4e981c0ab9bb`
- Source: `C:\Users\musst\.codex\sessions\2026\08\24\rollout-2026-08-24T09-48-47-01a03250-70fd-71e2-bbf8-4e981c0ab9bb.jsonl:1`
- Result: session metadata has `cwd` = `D:\.agents\processforge`; it refers to the target but is not the original target work session.

PF-native late session:

- `codex-20260824-inside-audit`
- Source: `D:\.agents\processforge-workplace\runtime\agent-ledger\sessions.ndjson:1323-1324`
- Result: checked in at `2026-08-24T07:12:42Z`, expired at `2026-08-24T07:20:07Z`.

Run/task ids:

- Run: `run-process-forge-inside-audit-20260824`
- Task: `task-process-forge-inside-audit-20260824`
- Run completed event: `evt_876e0b58d1aa4608bf08a5ace35abf74`
- Run correlation id: `run-run-process-forge-inside-audit-20260824`

## Codex Hooks

Evidence command:

```powershell
$paths=@(
  'D:\Dev\wt-read-in-ai\.codex\hooks.json',
  'C:\Users\musst\.codex\hooks.json',
  'D:\Dev\process-forge\.codex\hooks.json'
)
foreach($p in $paths){ if(Test-Path $p){ "FOUND $p"; Get-Content $p } else { "MISSING $p" }}
Select-String -Path C:\Users\musst\.codex\config.toml -Pattern 'mcp_servers.processforge|hooks.state|approval_policy|sandbox_mode' -Context 0,3
codex mcp list
```

Result:

- `D:\Dev\wt-read-in-ai\.codex\hooks.json`: missing.
- `C:\Users\musst\.codex\hooks.json`: missing.
- `D:\Dev\process-forge\.codex\hooks.json`: present and declares ProcessForge hook command for `SessionStart`, `SessionEnd`, `PostToolUse`, `UserPromptSubmit`, `PreCompact`, `PostCompact`, `Stop`, `SubagentStop`: `py -3 "D:\Dev\process-forge\tools\pf_runtime\codex_hooks.py"`.
- `C:\Users\musst\.codex\config.toml`: `approval_policy = "never"`, `sandbox_mode = "danger-full-access"`, `[mcp_servers.processforge]` command `python D:\.agents\processforge\tools\pf_runtime\mcp_server.py --workplace D:\.agents\processforge-workplace`, `[hooks.state]` exists but no hook table was found in the inspected excerpt.
- `codex mcp list`: `processforge` enabled; also `serena`, `playwright`, `context7`, `chrome_devtools`, `node_repl`, `phpstorm`.

Conclusion: ProcessForge MCP is globally configured, but Codex hook configuration was not present in the target repo or global Codex home. The only hook JSON found is in the ProcessForge source checkout, not in the target project. This matches the absence of raw ingress rows for the target Codex ids.

## Raw Ingress Timeline

Evidence command:

```powershell
$ids=@(
  '01a03241-9d12-7ea3-953c-f52b3a241319',
  '01a03250-70fd-71e2-bbf8-4e981c0ab9bb',
  'codex-20260824-inside-audit'
)
foreach($id in $ids){
  rg -n --fixed-strings $id D:\.agents\processforge-workplace\runtime\agent-events D:\.agents\processforge-workplace\runtime\agent-ledger D:\.agents\processforge-workplace\runtime\agent-presence D:\.agents\processforge-workplace\runtime\current-sessions
}
```

Result:

- `01a03241-9d12-7ea3-953c-f52b3a241319`: no matches.
- `01a03250-70fd-71e2-bbf8-4e981c0ab9bb`: no matches.
- `codex-20260824-inside-audit`: Ledger/current-session/presence matches.

Raw event file check:

```powershell
$raw='D:\.agents\processforge-workplace\runtime\agent-events\raw\v1\2026\08\24\05.ndjson'
# Filter source_session_id for both target Codex ids.
```

Result: `NO_RAW_ROWS_FOR_TARGET_CODEX_IDS`.

Conclusion: no raw hook ingress was captured for the inferred original Codex sessions.

## Ledger Timeline

Evidence files:

- `D:\.agents\processforge-workplace\runtime\agent-ledger\sessions.ndjson`
- `D:\.agents\processforge-workplace\runtime\current-sessions\wt-read-in-ai.json`
- `D:\.agents\processforge-workplace\runtime\agent-presence\codex\codex-20260824-inside-audit.json`

Confirmed entries:

- `sessions.ndjson:1323`: `agent.checked_in`, session `codex-20260824-inside-audit`, project `wt-read-in-ai`, run `run-process-forge-inside-audit-20260824`, task `task-process-forge-inside-audit-20260824`, recorded `2026-08-24T07:12:42Z`.
- `sessions.ndjson:1324`: `agent.session_expired`, same session/run, recorded `2026-08-24T07:20:07Z`.
- `current-sessions\wt-read-in-ai.json`: status `online`, same session, last seen `2026-08-24T07:12:42Z`.
- `agent-presence\codex\codex-20260824-inside-audit.json`: status `stale`, updated `2026-08-24T07:20:07Z`.

Conclusion: the late PF-native session is Ledger-backed. The original Codex session ids are not Ledger-backed. There is also a projection inconsistency: current-sessions says `online` after Ledger has emitted `agent.session_expired` and presence says `stale`.

## MCP Replay

Available connected MCP tools:

- `pf_session_context`
- `pf_project_state`
- `pf_work_state`
- `pf_workplace_state`
- `pf_search`
- `pf_resolve`

The master prompt mentions `pf.session_activity` and `pf.session_chat`; those were visible in historical Codex transcripts, but they were not exposed in the current connected MCP tool list discovered by `tool_search` in this repeat run.

Replay set A: original Codex session id `01a03241-9d12-7ea3-953c-f52b3a241319`.

Calls and results:

- `mcp__processforge.pf_session_context(project_root='D:\Dev\wt-read-in-ai', session_id='01a03241-9d12-7ea3-953c-f52b3a241319')` -> `{"error":{"code":"unknown_session"}}`
- `mcp__processforge.pf_project_state(...)` -> `FAIL: runtime session is not routed by Agent Ledger`
- `mcp__processforge.pf_work_state(...)` -> `FAIL: runtime session is not routed by Agent Ledger`
- `mcp__processforge.pf_search(..., query='Joomla asset loading')` -> `FAIL: runtime session is not routed by Agent Ledger`
- `mcp__processforge.pf_resolve(..., resource_id='platform.joomla')` -> `FAIL: runtime session is not routed by Agent Ledger`

Replay set B: PF-native session id `codex-20260824-inside-audit`.

Calls and results:

- `pf_session_context` -> returns session context with active agent status `stale`, context freshness `stale`, execution readiness `blocked`, missing `filesystem.read` and `filesystem.write`, recent PF run events, and work projection falling back to `first-assignment`.
- `pf_project_state` -> `context_status: stale`, `policy_action: ask_operator`, project id `wt-read-in-ai`.
- `pf_work_state` -> shows current session status `online`, presence status `stale`, event count `69`, current work projection `first-assignment`.
- `pf_search(..., query='Joomla asset loading')` -> `{"error":{"code":"snapshot_not_fresh"}}`
- `pf_resolve(..., resource_id='platform.joomla')` -> `{"error":{"code":"snapshot_not_fresh"}}`

Conclusion: MCP works for a manually registered PF-native session, but it does not route the original Codex id. Search/resolve remain blocked by snapshot freshness even for the PF-native session.

## Snapshot / Resource / Search State

Evidence command:

```powershell
python .pf\runtime\bin\pf.py project-context-check --project-root .
python .pf\runtime\bin\pf.py search-index status --project-root . --workplace D:\.agents\processforge-workplace --verify-files
python .pf\runtime\bin\pf.py search-index doctor --workplace D:\.agents\processforge-workplace
```

Confirmed context state:

- Snapshot id: `ctx-20260731-082954-7f485f`
- Status: `stale`
- Policy action: `ask_operator`
- Recommended action: `project-context-refresh`
- Stale reasons: `valid_until expired`, `workplace_manifest` changed, process-pack registry changed, MCP registry changed, project classification changed.
- Resource readiness: `fresh`
- Execution readiness: `blocked`
- Missing capabilities: `filesystem.read`, `filesystem.write`

Search index state:

- Search DB: `D:\.agents\processforge-workplace\runtime\search\local-resource-search.sqlite`
- SQLite counts: `resources=25`, `documents=25`, `index_state=6`
- `search-index status` for target project: stale, resources `0`, documents `0`, `ERROR: scope_not_indexed`.
- `search-index doctor`: SQLite/FTS5 readable, failed file count zero, warnings for stale context and stale search index.

Code evidence:

- `D:\.agents\processforge\src\processforge_core\local_resource_search.py:635`: no row for the computed scope key returns `scope_not_indexed`.
- `D:\.agents\processforge\tools\pf_runtime\mcp_server.py:108-115`: `pf.resolve` and `pf.search` raise `snapshot_not_fresh` unless context status is `fresh` or `fresh_with_updates`.

Conclusion: the local resource search subsystem is present, but the target project's current snapshot scope is not indexed and MCP search is deliberately blocked by stale snapshot policy.

## Knowledge Usage Evidence

Codex transcript evidence:

```powershell
# Structured JSONL count of response_item.payload.type == function_call
```

Primary target transcript `01a03241...` function call counts:

- `exec_command=242`
- `pf_search=6`
- `pf_resolve=2`
- `pf_session_context=4`
- `pf_project_state=4`
- `pf_work_state=4`
- `pf_session_activity=2`
- `pf_session_chat=1`
- `pf_project_initialization_status=3`
- Serena/IDE use: `activate_project=2`, `get_symbols_overview=3`, `search_for_pattern=1`
- Memory use: `list_memories=1`, `read_memory=4`, `write_memory=4`

Diagnostic transcript `01a03250...` function call counts:

- `exec_command=261`
- `pf_search=6`
- `pf_resolve=6`
- `pf_session_context=7`
- `pf_project_state=6`
- `pf_work_state=5`
- `pf_session_activity=2`
- `pf_session_chat=2`
- `execute_tool=2`
- `update_plan=7`
- Serena use: `activate_project=7`, `search_for_pattern=4`

Selected PF MCP call lines:

- Primary transcript: `65-70`, early PF project/work/session calls without explicit session id.
- Primary transcript: `837-843`, `pf_search` and `pf_resolve` calls without explicit session id.
- Primary transcript: `1006-1030`, PF-native `codex-20260824-inside-audit` calls after explicit bootstrap.
- Diagnostic transcript: `565`, `718-722`, `949-954`, `1357-1362`, original Codex id replay.
- Diagnostic transcript: `965-969`, `1375-1379`, PF-native session replay.

Conclusion: the agents did use PF MCP and local file search during diagnosis. That usage was not enough to bind the original Codex session to Ledger; it mostly exposed the absence of routing and the stale search state.

## Assignment / Run Governance

Evidence commands:

```powershell
python .pf\runtime\bin\pf.py run-list --project-root .
python .pf\runtime\bin\pf.py run-status --project-root . --run run-process-forge-inside-audit-20260824
python .pf\runtime\bin\pf.py run-doctor --project-root . --run run-process-forge-inside-audit-20260824 --runtime-events
```

Result:

- `run-process-forge-inside-audit-20260824`: `completed`, title `ProcessForge inside audit 2026-08-24`.
- `run-read-with-ai-20260731`: `completed`, older plugin run.
- `run-status`: task `task-process-forge-inside-audit-20260824 [done]`.
- `run-doctor --runtime-events`: all checks PASS, including completed run summary and handoff.

Conclusion: the late inside audit was governed correctly after explicit PF bootstrap. The original Joomla-way/self-audit work earlier on 2026-08-24 was not started as a fresh first-class run.

## Artifact Trace

Evidence command:

```powershell
Get-ChildItem .pf\reviews, .pf\artifacts, .pf\runs\run-process-forge-inside-audit-20260824, .pf\handoffs\runs -File |
  Where-Object {$_.LastWriteTime -ge [datetime]'2026-08-24'} |
  Sort-Object LastWriteTime
```

Observed target artifacts:

| Local time | Path | Size | Classification |
| --- | --- | ---: | --- |
| 2026-08-24 09:46:42 | `.pf/reviews/joomla-way-code-audit-20260824.md` | 4199 | original review artifact |
| 2026-08-24 10:00:18 | `.pf/artifacts/processforge-device-audit-20260824.md` | 6380 | device audit artifact |
| 2026-08-24 10:00:28 | `.pf/reviews/process-forge-work-self-audit-20260824.md` | 8816 | self-audit artifact |
| 2026-08-24 11:09:42 | `.pf/artifacts/process-forge-inside-audit-master-prompt.md` | 9816 | copied inside-audit prompt |
| 2026-08-24 11:12:21 | `.pf/runs/run-process-forge-inside-audit-20260824/plan.md` | 218 | late run plan |
| 2026-08-24 11:19:53 | `.pf/runs/run-process-forge-inside-audit-20260824/summary.md` | 416 | late run summary |
| 2026-08-24 11:19:53 | `.pf/handoffs/runs/run-process-forge-inside-audit-20260824-handoff.md` | 153 | late run handoff |
| 2026-08-24 11:19:53 | `.pf/runs/run-process-forge-inside-audit-20260824/task-index.md` | 278 | late run task index |
| 2026-08-24 11:19:53 | `.pf/runs/run-process-forge-inside-audit-20260824/run.yaml` | 958 | late run state |
| 2026-08-24 11:20:37 | `.pf/reviews/process-forge-inside-audit-20260824.md` | 29945 | late inside-audit report |

Conclusion: `.pf` has durable artifacts, but the durable governance boundary only becomes strong for the 11:12-11:20 inside-audit run.

## Chat Trace

Evidence command:

```powershell
Get-ChildItem D:\Dev\wt-read-in-ai\.pf\runtime\chat -File -Recurse
Get-Content D:\Dev\wt-read-in-ai\.pf\runtime\hooks\outbox\wtaicc\evt_876e0b58d1aa4608bf08a5ace35abf74.wtaicc-outbox.json
```

Result:

- `chat_files=0`
- Run completed outbox payload contains:
  - `chat.included=false`
  - `messages=[]`
  - `mode=metadata_only`
  - `event.session.id=null`

Conclusion: ProcessForge did not capture Codex chat content for the target work. The outbox payloads are event metadata only.

## PF Event / Hook / Outbox Trace

Evidence command:

```powershell
$events='D:\Dev\wt-read-in-ai\.pf\runtime\events\events.ndjson'
# ConvertFrom-Json and Group-Object event_type
Get-ChildItem D:\Dev\wt-read-in-ai\.pf\runtime\hooks\outbox\wtaicc -Filter *.json -File
Get-ChildItem D:\Dev\wt-read-in-ai\.pf\runtime\hooks\results -Filter *.json -File
```

Result:

- `events_count=69`
- `wtaicc_outbox_count=68`
- `results_count=68`
- event type counts:
  - `artifact.updated=15`
  - `tool.invoked=6`
  - `run.doctor.passed=6`
  - `capability.missing=6`
  - `run.summary.created=4`
  - `mcp.invoked=3`
  - `assignment.created=3`
  - `context.snapshot.refreshed=3`
  - `task.completed=2`
  - `assignment.started=2`
  - `task.created=2`
  - `run.created=2`
  - `run.completed=2`
  - `assignment.completed=2`
  - `task.started=2`
  - plus single onboarding/project/doctor events.

Hook config:

- `.pf/hooks.yaml`: mode `outbox`, `network_send_enabled: false`.
- Target `wtaicc-outbox`: enabled, path `.pf/runtime/hooks/outbox/wtaicc`, event types `*`.
- Policy: `chat_content_requires_opt_in: true`, `outbox_hooks_are_non_blocking: true`.

Conclusion: PF internal runtime events and outbox delivery work for PF CLI-generated events. They do not prove Codex hook ingress for the original session because the Codex raw ingress and Ledger rows are absent.

## Doctor Findings

`project-context-check`:

- `STATUS: stale`
- `POLICY_ACTION: ask_operator`
- `RESOURCE_READINESS: fresh`
- `EXECUTION_READINESS: blocked`
- missing `filesystem.read`, `filesystem.write`

`doctor-project`:

- FAIL `.gitignore missing .pf/process-forge.local.yaml`
- FAIL required capability registry declarations are missing: `filesystem.read`, `filesystem.write`
- Many manifest, hook, knowledge index, onboarding artifact checks PASS.

`run-doctor --runtime-events` for `run-process-forge-inside-audit-20260824`:

- PASS run schema/status/process.
- PASS task status and assignment linkage.
- PASS completed run has all blocking tasks done.
- PASS summary and handoff exist.
- PASS runtime run events exist.

Conclusion: project-level readiness is blocked/stale, while the specific late audit run is internally consistent.

## Legacy Path Findings

Evidence command:

```powershell
Select-String -Path D:\.agents\platforms\joomla\platform.json -Pattern 'joomla-toolkit|root|required' -Context 0,1
Test-Path D:\.agents\docs\joomla-toolkit
Test-Path D:\.agents\docs\joomla\core\joomla-toolkit
rg -n "relative_path: joomla/core/joomla-toolkit|D:/.agents/docs/joomla-toolkit|docs.joomla-toolkit" D:\Dev\wt-read-in-ai\.pf\contexts D:\.agents\processforge-workplace\platform-contracts D:\.agents\processforge-workplace\registries
```

Result:

- `D:\.agents\platforms\joomla\platform.json:31-34` still references `D:/.agents/docs/joomla-toolkit/`.
- `D:\.agents\docs\joomla-toolkit`: missing.
- `D:\.agents\docs\joomla\core\joomla-toolkit`: exists.
- Current PF snapshots and workplace contract route `docs.joomla-toolkit:root` through `relative_path: joomla/core/joomla-toolkit`.

Conclusion: the legacy platform JSON contains stale path references. The current ProcessForge snapshot/resource path uses the corrected `joomla/core/joomla-toolkit` route.

## Confirmed Defects

### DEFECT-PF-001 - Target Codex sessions absent from raw ingress and Ledger

Evidence:

- `rg --fixed-strings` over `agent-events`, `agent-ledger`, `agent-presence`, `current-sessions`: no matches for `01a03241...` or `01a03250...`.
- Raw file `agent-events\raw\v1\2026\08\24\05.ndjson`: `NO_RAW_ROWS_FOR_TARGET_CODEX_IDS`.

Impact: PF cannot reconstruct the original Codex session through the intended raw ingress -> normalized event -> Ledger path.

### DEFECT-PF-002 - MCP cannot route original Codex session id

Evidence:

- `pf_session_context` with `01a03241...`: `unknown_session`.
- `pf_project_state`, `pf_work_state`, `pf_search`, `pf_resolve` with `01a03241...`: not routed by Agent Ledger.

Impact: MCP replay cannot provide reliable session-bound project context for the original work session.

### DEFECT-PF-003 - Snapshot freshness blocks MCP search/resolve

Evidence:

- `project-context-check`: status `stale`, policy `ask_operator`.
- `pf_search` with PF-native session: `snapshot_not_fresh`.
- `pf_resolve(resource_id='platform.joomla')` with PF-native session: `snapshot_not_fresh`.
- Code: `mcp_server.py:108-115`.

Impact: PF search over authorized local resources is unavailable until the project context is refreshed.

### DEFECT-PF-004 - Execution readiness blocked by capability registry

Evidence:

- `project-context-check`: missing `filesystem.read`, `filesystem.write`.
- `doctor-project`: required capability registry declarations missing.

Impact: project readiness reports blocked even though the shell runtime has actual filesystem access.

### DEFECT-PF-005 - Chat capture absent

Evidence:

- `.pf/runtime/chat`: zero files.
- outbox payload `evt_876e0b58...wtaicc-outbox.json`: `chat.included=false`, `messages=[]`, `mode=metadata_only`.

Impact: PF artifacts cannot audit Codex conversation content unless transcript JSONL is inspected outside PF.

### DEFECT-PF-006 - Session projection inconsistency

Evidence:

- Ledger has `agent.session_expired` for `codex-20260824-inside-audit` at `2026-08-24T07:20:07Z`.
- Presence file status is `stale`.
- Current-sessions file status is still `online`.

Impact: current session projection can mislead auditors after TTL expiry.

## Expected Behavior

For a fully working PF-on-Codex integration, a target Codex work session should produce:

- Codex hook `SessionStart` raw ingress with the real Codex session id.
- Post-tool raw ingress rows tied to the same session id.
- Normalized PF events with causation/correlation linking tool events to project/run/task state.
- Agent Ledger check-in or routing for the real Codex session id, not only a manual PF-native substitute id.
- MCP `pf_session_context`, `pf_project_state`, `pf_work_state`, `pf_search`, and `pf_resolve` usable with the real Codex session id.
- Search index fresh enough for snapshot-authorized local knowledge queries, or a clear first-run refresh action.
- Durable assignment/run artifacts created before substantive project work, not retroactively.

## False Positives / Misleading Diagnostics

`doctor-project` reports `.gitignore missing .pf/process-forge.local.yaml`.

Counter-evidence:

```powershell
git check-ignore -v .pf/process-forge.local.yaml .pf/runtime/events/events.ndjson .pf/reviews/process-forge-work-self-audit-20260824.md
```

Result:

- `.gitignore:1:.pf/` ignores all checked paths.

Classification: misleading diagnostic / strict exact-pattern policy. It is not a current public exposure defect.

## Uncertain Findings

- The exact root cause for absent Codex hook ingress is not proven from local evidence alone. The evidence supports a hook loading/delivery gap because target/global `hooks.json` are missing and raw ingress has no rows, but it does not prove whether Codex intentionally ignores repo-local hooks outside the current checkout, whether hook config scope was wrong, or whether host hook execution failed before writing raw ingress.
- The historical `pf.session_activity` and `pf.session_chat` MCP tools appear in Codex transcripts, but the connected ProcessForge MCP tool list exposed in this repeat run did not include them. This may be a current tool exposure/version difference rather than deletion of the underlying functions.
- The search DB contains fresh scopes for other snapshots, but not for the target project's current stale snapshot scope. This is enough to explain `scope_not_indexed`; it does not prove whether an index refresh would fully succeed after context refresh.

## Inside-vs-Outside Comparison

Inside report claim: PF worked after explicit `session-start`.

Outside finding: confirmed for `codex-20260824-inside-audit`. Ledger, run/task files, runtime events, outbox, summary, handoff, and `run-doctor --runtime-events` support this.

Inside report claim: before explicit session-start, MCP/raw ingress were missing for the real Codex session.

Outside finding: confirmed. Original Codex ids are absent from raw ingress and Ledger; MCP rejects `01a03241...`.

Inside report claim: PF search is blocked by stale snapshot.

Outside finding: confirmed. `project-context-check`, `search-index status`, and MCP replay all converge on stale/snapshot_not_fresh/scope_not_indexed.

Inside report claim: hooks/outbox work for PF events but not chat/raw Codex capture.

Outside finding: confirmed with nuance. PF CLI events write 68 payloads to `.pf/runtime/hooks/outbox/wtaicc` and 68 result files. Chat is metadata-only and raw Codex ingress is absent.

Inside report claim: final Git public tree remained clean.

Outside finding: target Git is `## main...origin/main`. `.pf` artifacts are ignored and do not affect public tracked state.

## Recommendations

1. Add an installation doctor that validates effective Codex hook loading for the actual target checkout, not only existence of `D:\Dev\process-forge\.codex\hooks.json`.
2. Emit a clear `codex_hook_not_loaded` / `session_not_observed` diagnostic when MCP sees a Codex session id that is absent from raw ingress and Ledger.
3. Update current-session projection on `agent.session_expired`, or expose stale/expired state directly in `pf_work_state`.
4. Split `doctor-project` `.gitignore` checks into "exact policy entry missing" and "effective Git ignore protection present".
5. Provide a safe one-command project context/search refresh flow that explains capability registry blockers before running.
6. Expose `pf_session_activity` and `pf_session_chat` consistently in the MCP tool schema if they remain supported.
7. Keep a documented distinction between PF internal runtime hooks/outbox and Codex host hooks/raw ingress; auditors currently have to infer that boundary from multiple files.

## Evidence Index

Master prompt:

- `D:\Dev\process-forge\задания\process-forge-outside-audit-master-prompt.md`

Primary target project:

- `D:\Dev\wt-read-in-ai`

Previous outside audit artifacts:

- `D:\Dev\process-forge\.pf\artifacts\process-forge-outside-audit-20260824.md`
- `D:\Dev\process-forge\.pf\artifacts\process-forge-session-timeline-20260824.csv`

Repeat outside audit artifacts:

- `D:\Dev\process-forge\.pf\artifacts\process-forge-outside-audit-20260824-r2.md`
- `D:\Dev\process-forge\.pf\artifacts\process-forge-session-timeline-20260824-r2.csv`

Codex transcripts:

- `C:\Users\musst\.codex\sessions\2026\08\24\rollout-2026-08-24T09-32-36-01a03241-9d12-7ea3-953c-f52b3a241319.jsonl`
- `C:\Users\musst\.codex\sessions\2026\08\24\rollout-2026-08-24T09-48-47-01a03250-70fd-71e2-bbf8-4e981c0ab9bb.jsonl`

Agent Ledger and presence:

- `D:\.agents\processforge-workplace\runtime\agent-ledger\sessions.ndjson`
- `D:\.agents\processforge-workplace\runtime\current-sessions\wt-read-in-ai.json`
- `D:\.agents\processforge-workplace\runtime\agent-presence\codex\codex-20260824-inside-audit.json`
- `D:\.agents\processforge-workplace\runtime\agent-events\raw\v1\2026\08\24\05.ndjson`

Target PF files:

- `D:\Dev\wt-read-in-ai\.pf\process-forge.yaml`
- `D:\Dev\wt-read-in-ai\.pf\contexts\project-context.snapshot.yaml`
- `D:\Dev\wt-read-in-ai\.pf\hooks.yaml`
- `D:\Dev\wt-read-in-ai\.pf\runtime\events\events.ndjson`
- `D:\Dev\wt-read-in-ai\.pf\runtime\hooks\outbox\wtaicc\evt_876e0b58d1aa4608bf08a5ace35abf74.wtaicc-outbox.json`
- `D:\Dev\wt-read-in-ai\.pf\runtime\hooks\results\*.json`
- `D:\Dev\wt-read-in-ai\.pf\reviews\process-forge-work-self-audit-20260824.md`
- `D:\Dev\wt-read-in-ai\.pf\reviews\process-forge-inside-audit-20260824.md`
- `D:\Dev\wt-read-in-ai\.pf\runs\run-process-forge-inside-audit-20260824\run.yaml`

ProcessForge code and config:

- `D:\.agents\processforge\src\processforge_core\local_resource_search.py:635`
- `D:\.agents\processforge\tools\pf_runtime\mcp_server.py:108-115`
- `D:\Dev\process-forge\.codex\hooks.json`
- `C:\Users\musst\.codex\config.toml`
- `D:\.agents\processforge-workplace\runtime\search\local-resource-search.sqlite`

Commands materially used:

- `Get-Date -Format o`
- `hostname`
- `Get-CimInstance Win32_OperatingSystem`
- `python --version`
- `codex --version`
- `git status --short --branch`
- `python .pf\runtime\bin\pf.py version`
- `python .pf\runtime\bin\pf.py project-context-check --project-root .`
- `python .pf\runtime\bin\pf.py doctor-project --project-root .`
- `python .pf\runtime\bin\pf.py run-list --project-root .`
- `python .pf\runtime\bin\pf.py run-status --project-root . --run run-process-forge-inside-audit-20260824`
- `python .pf\runtime\bin\pf.py run-doctor --project-root . --run run-process-forge-inside-audit-20260824 --runtime-events`
- `python .pf\runtime\bin\pf.py search-index status --project-root . --workplace D:\.agents\processforge-workplace --verify-files`
- `python .pf\runtime\bin\pf.py search-index doctor --workplace D:\.agents\processforge-workplace`
- `rg --fixed-strings` over raw ingress, Ledger, presence, current-sessions
- `sqlite3 -readonly D:\.agents\processforge-workplace\runtime\search\local-resource-search.sqlite`
- `git check-ignore -v .pf/process-forge.local.yaml .pf/runtime/events/events.ndjson .pf/reviews/process-forge-work-self-audit-20260824.md`

Current repeat MCP calls:

- `mcp__processforge.pf_session_context(project_root='D:\Dev\wt-read-in-ai', session_id='01a03241-9d12-7ea3-953c-f52b3a241319')`
- `mcp__processforge.pf_project_state(project_root='D:\Dev\wt-read-in-ai', session_id='01a03241-9d12-7ea3-953c-f52b3a241319')`
- `mcp__processforge.pf_work_state(project_root='D:\Dev\wt-read-in-ai', session_id='01a03241-9d12-7ea3-953c-f52b3a241319')`
- `mcp__processforge.pf_search(project_root='D:\Dev\wt-read-in-ai', session_id='01a03241-9d12-7ea3-953c-f52b3a241319', query='Joomla asset loading', limit=3)`
- `mcp__processforge.pf_resolve(project_root='D:\Dev\wt-read-in-ai', session_id='01a03241-9d12-7ea3-953c-f52b3a241319', resource_id='platform.joomla')`
- `mcp__processforge.pf_session_context(project_root='D:\Dev\wt-read-in-ai', session_id='codex-20260824-inside-audit')`
- `mcp__processforge.pf_project_state(project_root='D:\Dev\wt-read-in-ai', session_id='codex-20260824-inside-audit')`
- `mcp__processforge.pf_work_state(project_root='D:\Dev\wt-read-in-ai', session_id='codex-20260824-inside-audit')`
- `mcp__processforge.pf_search(project_root='D:\Dev\wt-read-in-ai', session_id='codex-20260824-inside-audit', query='Joomla asset loading', limit=3)`
- `mcp__processforge.pf_resolve(project_root='D:\Dev\wt-read-in-ai', session_id='codex-20260824-inside-audit', resource_id='platform.joomla')`
