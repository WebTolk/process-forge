# Session Replay Code Review

**Вердикт: FAIL**

## Критичное замечание

1. Slice не проходит acceptance по доказательной части: в разрешённом срезе есть реализация и smoke, но нет набора focused tests, который прямо требует дизайн.
   Доказательства:
   - Дизайн требует не только internal replay function, но и `tests` как минимально приемлемую поставку: `.pf/artifacts/central-agent-event-ingress-20260814/session-replay-slice-design.md:158-201`.
   - В доступном срезе единственный assurance-артефакт кроме кода это `tools/smoke_central_event_replay.py:1-155`.
   - Smoke покрывает happy/idempotent path: initial repair, `unsupported_mapping`, cross-project `denied`, повторный `present`, повторный repair после ручного удаления события (`tools/smoke_central_event_replay.py:122-146`).
   - Smoke не покрывает ключевые failure rules из дизайна: остановку на malformed JSON без продвижения checkpoint и непродвижение checkpoint после ошибки repair (`session-replay-slice-design.md:134-141`, `:181-189`).

## Проверка реализации

- `PASS` Raw filtering реализован по raw v1 journal и key-фильтрам `schema_version/provider/adapter/source_session_id`: `tools/pf_runtime/session_replay.py:98-123`. Project containment затем проверяется через `source_project_ref -> resolve_project(...) == project_root`: `tools/pf_runtime/session_replay.py:136-140,166-172`.
- `PASS` Codex mapping boundary сохранена: replay импортирует и вызывает только `codex_hooks.normalized_event`, не кодирует локальный mapping (`tools/pf_runtime/session_replay.py:15-17,141-145`). Это соответствует дизайну `session-replay-slice-design.md:46-53,88-95`.
- `PASS` Missing-only behavior соблюдён: сначала вычисляется `stable_event_id`, затем `event_exists`, и только при отсутствии вызывается `_ingest_derived_event(...)` (`tools/pf_runtime/session_replay.py:151-163`). Host side semantics совпадают с текущим путём событий (`tools/pf_runtime/host.py:349-371,570-600`).
- `PASS` Project/session containment усилен дополнительно на derived-слое: `_derived_scope_allowed(...)` сверяет `project_root/cwd` и `session_id` до repair (`tools/pf_runtime/session_replay.py:147-181`).
- `PASS` Checkpoint пишется только после завершённых `present/repaired/unsupported_mapping/denied` результатов: запись идёт после `_process_record(...)`, а при `failed` функция возвращает результат до `_write_checkpoint(...)` (`tools/pf_runtime/session_replay.py:61-90`). Сам checkpoint session-scoped и атомарный (`tools/pf_runtime/session_replay.py:184-214`, `tools/pf_runtime/raw_ingress_kernel.py:107-133`).
- `PASS` Windows-safe persistence выглядит корректно в рамках среза: путь ограничен через `contained_path(...)`, запись идёт во временный файл в той же директории и завершается `os.replace(...)` (`tools/pf_runtime/raw_ingress_kernel.py:107-133`).
- `PARTIAL` Scope creep по chat/public CLI в просмотренном срезе не найден: `session_replay.py` объявлен как private helper без CLI (`tools/pf_runtime/session_replay.py:1-5`), smoke вызывает функцию напрямую (`tools/smoke_central_event_replay.py:16,122,139,144`), в `host.py` нет replay-команды среди видимых `command_*` entrypoints (`tools/pf_runtime/host.py:559,691,874,925,939`). Но полный запрет на public CLI нельзя доказать окончательно без чтения dispatcher-файла вне `allowed_read_files`.

## Ограничения проверки

- Smoke не запускался: задание read-only, а сам smoke создаёт `.tmp` и runtime state (`tools/smoke_central_event_replay.py:70-83,148-149`).
- Полное доказательство отсутствия public CLI registration вне `host.py` недоступно из-за ограниченного scope чтения.

## Итог

По самой реализации явного расхождения с design-семантикой не видно. Итоговый `FAIL` связан с тем, что acceptance в design требует focused tests, а в доступном срезе есть только smoke, который не доказывает failure-path требования для checkpoint/malformed input.
