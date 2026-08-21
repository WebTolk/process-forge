# Conversation completeness implementation report

## Delivered

- `codex_exec_worker.py` now builds one UTF-8 payload, persists it through a private raw-first `WorkerPromptPayloadSubmitted` envelope immediately before `codex exec`, and fails closed for a prepared PF worker if the input transcript receipt is not accepted.
- `host.ingest_event()` now routes optional `derived_conversation_messages[]` after an accepted raw receipt and before telemetry. It keeps denied content raw-only, enforces session/project routing, refuses unsafe automatic content and permits assistant content only from the PF-owned expected-report source.
- `append_chat_message()` accepts deterministic ids and serializes check/append/event emission under a transcript lock, preserving UUID behaviour for manual chat records.
- `command_worker_run_collect()` reads only the collectible expected report and captures it as one assistant message before task completion; stdout, stderr and lifecycle records remain non-conversation data.
- `codex_hooks.py` maps only a textual `UserPromptSubmit` to a user conversation message. Lifecycle/tool hooks remain telemetry-only.
- Added and release-registered `smoke_conversation_completeness.py`.

## Verification

- `python tools/smoke_conversation_completeness.py` — PASS.
- `python tools/smoke_codex_exec_worker.py` — PASS.
- `python tools/smoke_worker_run_shell.py` — PASS.
- `python tools/smoke_central_event_ingress.py` — PASS.
- `python tools/processforge.py release-test --root . --only smoke_codex_exec_worker --only smoke_conversation_completeness --no-clean` — PASS.
- `python -m py_compile` for all changed Python modules — PASS.
- `git diff --check` — PASS.

## Boundary

Generic Codex assistant-response hooks remain unsupported. This slice stores assistant content only from the collectible PF-owned expected-report file and adds no public API or network delivery.
