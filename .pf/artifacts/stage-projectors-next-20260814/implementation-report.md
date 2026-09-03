# Реализация: automatic stage projectors

Дата: 2026-08-14

## Результат

Реализован первый declaration-driven technical projector:
`required-output-readiness` для `process-supervisor:collect`.

- `process-supervisor.yaml` объявляет `technical_obligations`, а schema
  ограничивает их компактный контракт. Runtime не содержит stage-specific
  правила.
- Runtime Host читает declaration, assignment, Inspector agent-run state и
  разрешённые output paths; атомарно пишет
  `.pf/artifacts/projections/stage-obligations.json`.
- В projection есть readiness, observed output facts, SHA-256 и
  `source_fingerprint`. Reader различает `current`, `stale`, `missing` и
  `invalid`.
- `runtime-host rebuild-projections` пересобирает старый command history и
  новый stage snapshot; `projection-doctor` проверяет последний отдельно.
- Runtime scheduler запускает тот же rebuild, а `pf.work_state`/read-only MCP
  публикует current projection без нового MCP state или write API.
- Новая focused smoke проверяет rebuild, missing, stale, deletion/rebuild,
  semantic-artifact protection, Project A/B isolation и work-state exposure.

## Проверки

| Проверка | Результат |
| --- | --- |
| `python -m py_compile tools/processforge.py tools/pf_runtime/host.py tools/pf_runtime/service.py` | PASS |
| `python tools/validate-process-forge-schemas.py --root .` | PASS |
| `python tools/smoke_stage_projectors.py` | PASS |
| `runtime-host rebuild-projections` + `projection-doctor` | PASS |
| Real Codex hook session + Runtime scheduler + restart + stdio MCP `pf.work_state` | PASS; см. `live-validation.md` |
| `python tools/smoke_runtime_ledger_hooks_mcp.py` | PASS |

## Не включено

`changed-files` сознательно не реализован: normalised hook events не несут
восстанавливаемого списка путей/команд, поэтому snapshot `git diff` после
restart не мог бы быть authoritative. Не изменялись Agent Director,
platform-resolution/classification, daemon lifecycle, журнал событий, Ledger
или MCP write surface.

## Следующий контроль

Независимый PF shell-worker review должен проверить, что projector не
перезаписывает semantic artifacts, что declaration действительно остаётся
источником stage obligation и что нет регрессии на существующих runtime paths.

## Итоговая live remediation и review

Во время независимого Spark review живой Runtime выявил два ранее скрытых
defect в detached Codex driver: supervisor терял prepared driver при
наблюдении, а worker не публиковал durable exit contract. Они устранены и
покрыты `smoke_codex_exec_worker.py`. Повторный `gpt-5.3-codex-spark` worker
завершился штатно (`codex-exec`, 3600 seconds, `exit_code: 0`, `exit.json`) и
создал PASS review `stage-projectors-next-20260814-review-retry.md`.
