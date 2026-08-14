# Финальный регрессионный отчёт

## Цель среза

Провести отдельный current-work-state verification-slice без правок исходников и зафиксировать результаты в виде разделённой таблицы: **цель среза** vs **известные внешние root-провалы**.

## Evidence table

| Сегмент | Проверка | Команда | Результат | Статус | Примечание |
|---|---|---|---|---|---|
| синтаксис | Компиляция python | `python -m py_compile tools/pf_runtime/host.py tools/smoke_stage_projectors.py tools/smoke_verification_current_work_state.py` | Успех | ✅ PASS | Нет синтаксических регрессий в целевых файлах. |
| схема | Валидация схем | `python tools/validate-process-forge-schemas.py --root .` | PASS | ✅ PASS | Структурная схема проекта в порядке. |
| events | Валидация событий | `python tools/processforge.py events-validate --project-root .` | PASS | ✅ PASS | Runtime/chats-события валидны. |
| release-hygiene | `release-check` | `python tools/processforge.py release-check` | PASS | ✅ PASS | Базовый релизный чеклист проходит. |
| release (partial) | `release-test` | `python tools/processforge.py release-test` | FAIL/таймаут в середине (147.5s) | ❌ FAIL | Невозможность полной фиксации из‑за текущей среды: блокировки `.pf/runtime/agent-runs/.../stderr.log`, ошибки очистки и cleanup временных каталогов `D:\temp\...` (`PermissionError: WinError 5`). |
| smoke | `smoke_stage_projectors` | `python tools/smoke_stage_projectors.py` | FAIL | ❌ FAIL | Останов на `init-workplace`: PermissionError при создании `.../workplace/runtime/events`, и несанкционируемая очистка temp (`D:\temp\...`, `WinError 5`). |
| smoke | `smoke_verification_current_work_state` | `python tools/smoke_verification_current_work_state.py` | FAIL | ❌ FAIL | Тот же инфраструктурный блок: `init-workplace` и cleanup temp-каталога падают по правам доступа. |
| diff | Дифф-грязь | `git diff --check` | PASS | ✅ PASS | Строки без whitespace-неконсистентностей. Есть предупреждения о будущем `LF->CRLF`, без ошибок проверки. |
| release-archive | Полная архивная валидация | `python tools/processforge.py release-archive-test` | не запущена | ⚪ SKIP | Нужен обязательный параметр `--archive <path>`. |

## Разделение от независящих провалов root-проверок

- `release-test` (внутри того же запуска) дожимает до `doctor-project` и фиксирует отсутствующие артефакты онбординга для связанного проекта (`.pf/START_AGENT_HERE.md`, `.pf/artifacts/project-*.md`, `.pf/reviews/*`, `.pf/handoffs/*` и др.); это не менялось этим срезом и относится к состоянию корневого проекта/онбординга.
- Предыдущий контур фиксации также отмечал отдельный root-провал: `projection-doctor` падает из‑за ранее существующего `runtime-readonly-review` с отсутствующим required-output.
- Ошибки `PermissionError` во временных директориях и блокировка `stderr.log` — инфраструктурные в текущем runtime/песочнице, не изменения в логике проверяемой реализации.
