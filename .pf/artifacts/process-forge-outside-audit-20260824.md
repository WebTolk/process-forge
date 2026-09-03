# ProcessForge Outside Audit 2026-08-24

## Executive Summary

Target project: `D:\Dev\wt-read-in-ai`.

Main finding: the original inside work on 2026-08-24 used project-local `.pf` files and PF CLI, but it was not bound to the ProcessForge Agent Ledger by its Codex thread id. Direct PF MCP calls during the work returned `missing_session`; later replay with the Codex id returns `unknown_session` or "not routed by Agent Ledger". Therefore that work is not recoverable through the intended Codex session -> raw ingress -> Ledger -> MCP chain.

The project has durable semantic artifacts (`.pf/reviews/joomla-way-code-audit-20260824.md`, `.pf/logs/orchestrator.md`, `.pf/reviews/process-forge-work-self-audit-20260824.md`), but for the 09:32-10:00 work they are file evidence, not first-class PF lifecycle artifacts linked to a fresh run. A later/concurrent PF run `run-process-forge-inside-audit-20260824` was created at `2026-08-24T07:12:21Z` (`11:12:21 +04`), after this outside-audit prompt was opened; it is real current PF state, but I do not attribute it to the earlier 09:32 Joomla-way audit.

Confirmed technical breaks:

- `INTEGRATION_DEFECT/high`: Codex thread ids `01a03241...` and `01a03250...` are absent from PF raw ingress and Ledger for `wt-read-in-ai`.
- `AGENT_PROCESS_VIOLATION/medium`: the original Joomla-way audit wrote reports/logs without a fresh PF assignment/run lifecycle.
- `PROJECT_STATE_PROBLEM/medium`: snapshot is stale and execution readiness is blocked by missing registry declarations for `filesystem.read` and `filesystem.write`.
- `DIAGNOSTIC_FALSE_POSITIVE/low`: `doctor-project` says `.gitignore` misses `.pf/process-forge.local.yaml`, but `git check-ignore -v` proves the file is ignored through `.gitignore:1:.pf/`.
- `EXPECTED_BEHAVIOR/informational`: no PF chat transcript content because chat capture is opt-in and outbox payloads are metadata-only.

## Environment

- Audit timestamp: `2026-08-24T11:19:21+04:00`, timezone `Europe/Saratov`.
- Hostname: `WebTolkNB`.
- OS: Microsoft Windows 11 Home, version `10.0.26200`, build `26200`, 64-bit.
- Python: `3.14.3`.
- PF version in target project: `ProcessForge 1.1.0`, spec `1.0`, schema bundle `1.0`.
- Project path: `D:\Dev\wt-read-in-ai`.
- Workplace path: `D:\.agents\processforge-workplace`.
- Distribution/core path used by Codex MCP: `D:\.agents\processforge`.
- Git state in target: branch `main`, `HEAD` `4061af0 Document root plugin packaging`, `origin/main` aligned, `git status --short --branch` returned only `## main...origin/main`.
- Outside-audit output path: `D:\Dev\process-forge\.pf\artifacts\process-forge-outside-audit-20260824.md`.

Evidence: `Get-Date -Format o`; `hostname`; `Get-CimInstance Win32_OperatingSystem`; `python --version`; `python .pf\runtime\bin\pf.py version`; `git status --short --branch`; `git log --oneline --decorate --max-count=5`; `codex mcp list`.

## Correlation Keys

- Target project id: `wt-read-in-ai`.
- Primary Codex thread candidate for inside work: `01a03241-9d12-7ea3-953c-f52b3a241319`.
- Later independent/device audit thread: `01a03250-70fd-71e2-bbf8-4e981c0ab9bb`.
- Late PF Ledger session id: `codex-20260824-inside-audit`.
- Historical completed run: `run-read-with-ai-20260731`.
- Late/concurrent run: `run-process-forge-inside-audit-20260824`.
- Late/concurrent assignment: `task-process-forge-inside-audit-20260824`.

The inside/self-audit evidence did not provide a stable Codex session id as a project artifact. I recovered the candidate ids from local Codex JSONL. That gap is an audit defect because the main correlation key had to be inferred externally.

## Codex Hooks

Checked:

- `D:\Dev\wt-read-in-ai\.codex\hooks.json`: not present.
- `C:\Users\musst\.codex\hooks.json`: not present.
- `C:\Users\musst\.codex\config.toml`: target project `d:\dev\wt-read-in-ai` is trusted, MCP `processforge` is enabled, `[hooks.state]` is empty.
- `D:\Dev\process-forge\.codex\hooks.json`: present and declares `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `PreCompact`, `PostCompact`, `PostToolUse`, all invoking `py -3 "D:\Dev\process-forge\tools\pf_runtime\codex_hooks.py"`.

Conclusion: Codex hooks were configured for the ProcessForge source checkout, not for `D:\Dev\wt-read-in-ai` or global Codex config. For the investigated `wt-read-in-ai` sessions, raw ingress absence is best classified as `HOST_LIMITATION/INTEGRATION_DEFECT`: host never delivered target-session hook events, or the host did not load hooks from the target project. PF outbox is not evidence of Codex hooks.

## Raw Ingress Timeline

Searches:

- `rg -n "01a03241-9d12-7ea3-953c-f52b3a241319" D:\.agents\processforge-workplace\runtime\agent-events ...` returned no matches.
- Same search for `01a03250-70fd-71e2-bbf8-4e981c0ab9bb` returned no matches.
- Raw events exist for earlier `D:\Dev\process-forge` session `01a03220...` in `D:\.agents\processforge-workplace\runtime\agent-events\raw\v1\2026\08\24\05.ndjson`.

Result: no `SessionStart`, `UserPromptSubmit`, `PostToolUse`, `Stop`, `SubagentStop`, or `SessionEnd` raw ingress records for the target project Codex ids. Because there are no raw rows for those ids, loss is before PF raw ingress or at hook loading/delivery, not a normalized-event projection loss.

## Ledger Timeline

Ledger evidence:

- No Ledger or presence entry for `01a03241...` or `01a03250...`.
- `D:\.agents\processforge-workplace\runtime\agent-ledger\sessions.ndjson` contains `agent.checked_in` at `2026-08-24T07:12:42Z` for `session_id: codex-20260824-inside-audit`, `project_id: wt-read-in-ai`, `run_id: run-process-forge-inside-audit-20260824`.
- `D:\.agents\processforge-workplace\runtime\agent-presence\codex\codex-20260824-inside-audit.json` status is `online`, capabilities list includes `filesystem.read` and `filesystem.write`.
- `D:\.agents\processforge-workplace\runtime\current-sessions\wt-read-in-ai.json` points to `codex-20260824-inside-audit`.

Conclusion: Ledger was materialized for a PF-native session id, not for the Codex thread id. This explains why MCP reads with the real Codex id fail.

## MCP Replay

Replay with `session_id: 01a03241-9d12-7ea3-953c-f52b3a241319`:

- `pf.session_context`: `unknown_session`.
- `pf.project_state`, `pf.work_state`, `pf.search`, `pf.resolve`: `FAIL: runtime session is not routed by Agent Ledger`.
- `pf.session_activity`, `pf.session_chat`: `unknown_session`.

Replay with `session_id: codex-20260824-inside-audit`:

- `pf.session_context`: succeeds; reports stale context, execution blocked, active run `run-process-forge-inside-audit-20260824`, task `task-process-forge-inside-audit-20260824`.
- `pf.project_state`: succeeds; `context_status: stale`.
- `pf.work_state`: succeeds; active session and current run visible.
- `pf.session_activity`: succeeds; returns project events, mostly PF CLI events.
- `pf.session_chat`: succeeds with `messages: []`.
- `pf.search` and `pf.resolve`: fail with `snapshot_not_fresh`.

Conclusion: current MCP works only for the late PF session id. It cannot replay the original Codex session because no Ledger binding exists for that id.

## Snapshot/Resource/Search State

Project context:

- `project-context-check`: snapshot `ctx-20260731-082954-7f485f`, status `stale`, policy `ask_operator`.
- Stale reasons: expired `valid_until`, changed workplace manifest, changed process-pack registry, changed MCP registry, changed project classification.
- `RESOURCE_READINESS: fresh`.
- `EXECUTION_READINESS: blocked`.
- Missing capabilities: `filesystem.read`, `filesystem.write`.

Search:

- `search-index status --project-root . --workplace D:\.agents\processforge-workplace --verify-files`: `STATUS: stale`, `GENERATION: none`, `RESOURCES: 0`, `DOCUMENTS: 0`, `STALE_RESOURCES: 1`, `ERROR: scope_not_indexed`, index path `D:\.agents\processforge-workplace\runtime\search\local-resource-search.sqlite`.
- SQLite DB exists and is readable. Counts: `index_state=6`, `resources=25`, `documents=25`, `documents_fts=25`.
- `index_state` contains rows for other snapshot ids such as `ctx-20260824-052549-cea5dc`, but not the target snapshot `ctx-20260731-082954-7f485f`.
- Installed code `D:\.agents\processforge\src\processforge_core\local_resource_search.py` returns `scope_not_indexed` when the computed snapshot `scope_key` has no `index_state` row.

Conclusion: `scope_not_indexed` is a derived search-index authorization/scope-key state for the current snapshot, not proof that there is a separate project-specific SQLite database missing.

## Knowledge Usage Evidence

Original candidate thread `01a03241...` before `2026-08-24T07:00Z`:

- PF MCP calls: `pf_project_initialization_status=1`, `pf_project_state=2`, `pf_work_state=1`, `pf_session_context=2`.
- No `pf_search` or `pf_resolve` calls in that original segment.
- Direct file reads: `.pf/AGENTS.md`, `.pf/START_AGENT_HERE.md`, `.pf/process-forge.yaml`, `.pf/process-forge.local.yaml`, assignments, run files, reports.
- Local knowledge reads: `D:\.agents\docs\joomla\core\joomla-toolkit\...`, `D:\.agents\processforge-workplace\platform-contracts\platform.joomla\platform-contract.yaml`, Joomla core/docs paths.
- Search/discovery used `rg` and `Get-Content`.
- Context7/web/browser were not observed for the original segment.

Later `01a03250...` audit thread:

- Called `pf_search` and `pf_resolve`, but both were attempted without Ledger-bound session and failed.
- Ran `search-index status/doctor` via CLI.
- Used PhpStorm MCP for `git_status`; no evidence of Context7/web.

No verified chain exists of `pf.search -> pf.resolve -> filesystem read -> artifact` for the original inside work.

## Assignment/Run Governance

Before late run creation:

- `START_AGENT_HERE.md` pointed to `.pf/assignments/first-assignment.yaml`.
- `first-assignment.yaml` status was `open`; expected readiness note absent.
- Historical `task-001-read-with-ai-plugin.yaml` and `run-read-with-ai-20260731` were completed from July.
- The 09:32 Joomla-way audit wrote report/log artifacts but did not create a fresh run/assignment in the observed project events.

Current state after late activity:

- `run-list` shows `run-process-forge-inside-audit-20260824 in_progress` and `run-read-with-ai-20260731 completed`.
- Late run file `run.yaml` created at `2026-08-24T07:12:21Z`, assignment at `2026-08-24T07:12:32Z`, task started at `2026-08-24T07:12:42Z`.
- Ledger checked in `codex-20260824-inside-audit` at `2026-08-24T07:12:42Z`.

Answer: the original inside work exists as files/logs and Codex JSONL, not as a first-class PF execution lifecycle. The late inside-audit run is first-class PF state, but it is temporally after the original Joomla-way audit and is not bound to the original Codex thread id.

## Artifact Trace

Observed 2026-08-24 files in target project:

- `.pf/reviews/joomla-way-code-audit-20260824.md`, mtime `09:46:42 +04`, ignored by `.gitignore:1:.pf/`, semantic review exists, no matching `artifact.updated` event found for that write.
- `.pf/artifacts/processforge-device-audit-20260824.md`, mtime `10:00:18 +04`, ignored; produced by later independent/device audit, not original inside work.
- `.pf/reviews/process-forge-work-self-audit-20260824.md`, mtime `10:00:28 +04`, ignored; semantic self-audit exists.
- `.pf/logs/orchestrator.md`, mtime `10:00:28 +04`, ignored; append-only process log exists.
- `.pf/artifacts/process-forge-inside-audit-master-prompt.md`, mtime `11:09:42 +04`, ignored; prompt copy for late inside audit.
- `.pf/runs/run-process-forge-inside-audit-20260824/*`, mtime `11:12:21-11:12:42 +04`, ignored; first-class late run files.

Semantic file exists is not the same as PF artifact registration. For the original Joomla-way review, I found the file and log but not a corresponding PF artifact event or run linkage.

## Chat Trace

Policy evidence:

- `.pf/hooks.yaml` uses outbox mode.
- Network webhook target disabled.
- `chat_content_requires_opt_in: true`.
- Outbox payloads are `metadata_only`, with `chat.included: false` and empty message arrays.
- `.pf/runtime/chat` has no files.
- `pf.session_chat` for `codex-20260824-inside-audit` returns `messages: []`.

Classification: `EXPECTED_BEHAVIOR/informational`. Chat capture was not enabled for content, so absence of transcript is not a defect.

## PF Event/Hook/Outbox Trace

Project event file: `D:\Dev\wt-read-in-ai\.pf\runtime\events\events.ndjson`.

Key event chains:

- July governed plugin run: full PF events exist (`run.created`, `task.created`, `assignment.started`, `task.completed`, `run.completed`), plus hook outbox/results.
- Original 09:32 Joomla-way audit: no project PF event chain for report write; evidence is Codex JSONL plus ignored `.pf` files.
- Later 09:56 run-doctor checks: project events `evt_aaf...` and `evt_1df...` exist, with outbox/results. These were produced by later audit diagnostics, not the initial Joomla-way audit.
- Late 11:12 inside-audit run: events `run.created`, `task.created`, `assignment.created`, `task.started`, `assignment.started`; Ledger session exists.
- External audit diagnostics after 11:13 added `run.doctor.passed` events. These are explicitly excluded from the original inside-work assessment.

Codex raw ingress does not connect to these target project events for `01a03241...`.

## Doctor Findings

`doctor-project --project-root .`:

- FAIL `.gitignore missing .pf/process-forge.local.yaml`.
- FAIL required capability registry declarations missing: `filesystem.read`, `filesystem.write`.
- Knowledge resource indexes mostly pass, including Joomla resources.

`.gitignore` verification:

- `git check-ignore -v .pf/process-forge.local.yaml` returns `.gitignore:1:.pf/`.
- Classification: `DIAGNOSTIC_FALSE_POSITIVE/low` for actual exposure; possible `UX_GAP/low` because doctor demands explicit pattern.

Capabilities:

- `project-context-check` reports missing `filesystem.read` and `filesystem.write`, required by `project.required_capabilities`.
- Expected provider scope: project or workplace tool/MCP registry.
- Resource readiness remains `fresh`; execution readiness is `blocked`.
- Classification: `PROJECT_STATE_PROBLEM/medium`. Do not add fake providers.

## Legacy Path Findings

- `D:\.agents\platforms\joomla\platform.json` points to missing legacy root `D:/.agents/docs/joomla-toolkit/`.
- Actual current toolkit exists at `D:\.agents\docs\joomla\core\joomla-toolkit`.
- Target snapshot and workplace platform contract use `docs.joomla-toolkit` with `relative_path: joomla/core/joomla-toolkit`.

Classification: `STALE_LEGACY_STATE/low`. I found no evidence that current PF `pf.search`/`pf.resolve` used the stale `platform.json` path for the target snapshot; it is misleading routing residue outside the current workplace contract path.

## Confirmed Defects

| Type | Severity | Finding | Evidence |
| --- | --- | --- | --- |
| INTEGRATION_DEFECT | high | Codex target thread ids are not in PF raw ingress or Ledger | `rg` over workplace runtime returned no `01a03241...`/`01a03250...`; MCP replay returns `unknown_session` |
| AGENT_PROCESS_VIOLATION | medium | Original Joomla-way audit lacked first-class PF run/assignment lifecycle | No PF run/events before late 11:12 run; artifacts written as files |
| PROJECT_STATE_PROBLEM | medium | Execution readiness blocked by missing `filesystem.read/write` registry providers | `project-context-check`; `doctor-project` |
| PROJECT_STATE_PROBLEM | medium | Project context snapshot stale | `ctx-20260731-082954-7f485f`, expired and source changes |
| UX_GAP | low | Doctor demands explicit `.pf/process-forge.local.yaml` ignore despite broader `.pf/` ignore | `doctor-project` plus `git check-ignore -v` |

## Expected Behavior

- No chat transcript content because policy requires opt-in and outbox is metadata-only.
- `pf.search`/`pf.resolve` returning `snapshot_not_fresh` for Ledger-bound late session because target snapshot is stale.
- Workplace/resource-oriented SQLite index has rows for other scopes while target snapshot returns `scope_not_indexed`.

## False Positives / Misleading Diagnostics

- `.gitignore missing .pf/process-forge.local.yaml`: misleading as exposure finding. The file is ignored by `.gitignore:1:.pf/`.
- Self-report statements about 09:56 `run.doctor.*` events can mislead if read as original inside-agent governance. Outside timeline attributes those events to the later audit thread and CLI diagnostics.
- Calling the SQLite search index "project-specific" would be misleading; observed path is workplace runtime search DB.

## Uncertain Findings

- The exact mechanism that created `run-process-forge-inside-audit-20260824` at `11:12 +04` is not proven from raw Codex hooks because no matching Codex raw ingress exists. It is real PF state, but origin is only narrowed to PF CLI/processforge state.
- Stop/SessionEnd absence for target sessions cannot be assigned solely to PF loss; because SessionStart is absent too, the more likely point is host hook loading/delivery.

## Inside-vs-Outside Comparison

| Claim from inside/self audit | Observed outside | Status | Evidence |
| --- | --- | --- | --- |
| PF MCP did not work and returned `missing_session` | Original MCP calls returned `missing_session`; replay with Codex id returns `unknown_session`/not routed | confirmed | Codex JSONL, MCP replay |
| PF hooks worked for CLI-generated events | Project PF outbox/results exist for PF CLI events | confirmed | `.pf/runtime/events`, `.pf/runtime/hooks/outbox`, `.pf/runtime/hooks/results` |
| Codex hooks captured session | No target raw ingress for target Codex ids | contradicted/unconfirmed | workplace `agent-events` search |
| Chat logs absent | No `.pf/runtime/chat`; `pf.session_chat` empty | confirmed expected | hooks policy and MCP replay |
| New assignment/run was not created for Joomla-way audit | No first-class run for 09:32 audit; late run exists only after 11:12 | confirmed with timing caveat | run-list, events, mtimes |
| Artifacts were written | Review/log/self-audit files exist | confirmed | file mtimes |
| Artifacts registered in PF lifecycle | Original review has no observed `artifact.updated` event or run linkage | contradicted/partial | events.ndjson |
| Doctor failures exist | Current doctor fails on explicit ignore and capabilities | confirmed | command replay |
| `.gitignore` issue is actual exposure | File is ignored by `.pf/` pattern | contradicted | `git check-ignore -v` |
| Resource readiness fresh | `project-context-check` says `RESOURCE_READINESS: fresh` | confirmed | CLI |
| Search readiness usable | Target search status stale and `scope_not_indexed`; MCP search blocked by stale snapshot | contradicted | CLI, MCP, SQLite |

## Recommendations

1. Install or activate Codex hooks for `D:\Dev\wt-read-in-ai` or global Codex config if PF must capture real target sessions. Verify by creating a real new session and checking raw `SessionStart` before relying on MCP.
2. Bind Codex thread id to Agent Ledger automatically or record the PF-native session id in the inside report as a required output.
3. Require agents to create/select a PF assignment/run before writing project audit artifacts.
4. Refresh target project context before relying on `pf.search`/`pf.resolve`; do not rebuild the index blindly until snapshot freshness is addressed.
5. Fix or waive `filesystem.read/write` provider declarations through real registry evidence only.
6. Adjust `doctor-project` ignore check to use `git check-ignore` semantics or downgrade the explicit-pattern failure when `.pf/` already ignores the file.
7. Keep legacy `D:\.agents\platforms\joomla\platform.json` aligned with workplace contracts or mark it deprecated to avoid agent routing confusion.

## Evidence Index

- `D:\Dev\wt-read-in-ai\.pf\AGENTS.md`
- `D:\Dev\wt-read-in-ai\.pf\process-forge.yaml`
- `D:\Dev\wt-read-in-ai\.pf\process-forge.local.yaml`
- `D:\Dev\wt-read-in-ai\.pf\START_AGENT_HERE.md`
- `D:\Dev\wt-read-in-ai\.pf\hooks.yaml`
- `D:\Dev\wt-read-in-ai\.pf\assignments\first-assignment.yaml`
- `D:\Dev\wt-read-in-ai\.pf\assignments\task-001-read-with-ai-plugin.yaml`
- `D:\Dev\wt-read-in-ai\.pf\assignments\task-process-forge-inside-audit-20260824.yaml`
- `D:\Dev\wt-read-in-ai\.pf\runs\run-read-with-ai-20260731\run.yaml`
- `D:\Dev\wt-read-in-ai\.pf\runs\run-process-forge-inside-audit-20260824\run.yaml`
- `D:\Dev\wt-read-in-ai\.pf\runtime\events\events.ndjson`
- `D:\Dev\wt-read-in-ai\.pf\runtime\hooks\outbox\wtaicc\*.json`
- `D:\Dev\wt-read-in-ai\.pf\runtime\hooks\results\*.json`
- `D:\.agents\processforge-workplace\runtime\agent-events\raw\v1\2026\08\24\05.ndjson`
- `D:\.agents\processforge-workplace\runtime\agent-ledger\sessions.ndjson`
- `D:\.agents\processforge-workplace\runtime\agent-presence\codex\codex-20260824-inside-audit.json`
- `D:\.agents\processforge-workplace\runtime\current-sessions\wt-read-in-ai.json`
- `D:\.agents\processforge-workplace\runtime\search\local-resource-search.sqlite`
- `D:\.agents\processforge\src\processforge_core\local_resource_search.py`
- `D:\.agents\processforge\tools\pf_runtime\mcp_server.py`
- `C:\Users\musst\.codex\config.toml`
- `D:\Dev\process-forge\.codex\hooks.json`
- `C:\Users\musst\.codex\sessions\2026\08\24\rollout-2026-08-24T09-32-36-01a03241-9d12-7ea3-953c-f52b3a241319.jsonl`
- `C:\Users\musst\.codex\sessions\2026\08\24\rollout-2026-08-24T09-48-47-01a03250-70fd-71e2-bbf8-4e981c0ab9bb.jsonl`
- Timeline CSV: `D:\Dev\process-forge\.pf\artifacts\process-forge-session-timeline-20260824.csv`
