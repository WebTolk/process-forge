# Remediation: durable Codex worker exit contract

Дата: 2026-08-14

`codex_exec_worker.py` теперь после завершения Codex CLI атомарно записывает
`PF_AGENT_EXIT_PATH` с `{schema_version, exit_code, status}` и только затем
финальный heartbeat. Поэтому detached Inspector получает тот же durable факт,
что и запускающий CLI, и может собрать output без эвристики `unknown_exit`.

`smoke_codex_exec_worker.py` расширен прямым запуском worker через fake Codex:
он проверяет именно exit contract, а не только результат родительского
`worker-run start`.

Дополнительно `sync_failed_worker_lifecycle()` сохраняет semantic
`task.result.status: failed`; низкоуровневый `timed_out`/`unknown_exit` остаётся
в agent-run state и summary. Это сохраняет assignment schema-valid.

Проверки: `python tools/smoke_codex_exec_worker.py` — PASS;
`python tools/smoke_stage_projectors.py` — PASS.
