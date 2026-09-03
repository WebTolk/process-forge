# Аудит конвенции `session-replay` теста

## Результат
- **Статус: частичное соответствие (HIGH RISK).**
- Файл реализует релевантную логику `session-scoped replay`, но не соответствует действующим release-нормам проекта.

## Что проверено
- `.pf/artifacts/central-agent-event-ingress-20260814/session-replay-slice-design.md`
  Зафиксирован ожидаемый внутренний дизайн и набор из 8 фокус-тестов (строки 158–198).
- `tools/smoke_central_event_replay.py`
  Проанализирован smoke-скрипт (строки 1–243).
- `tools/processforge.py`
  Проанализированы регистрации `release-test` и `release-test`-конвейера (фрагменты вокруг `release_check`, `release_test`, `release_pack`, `release_archive_test` и `release_test_commands`).

## Найденные несоответствия

1. **Не зарегистрирован в `release-test` как отдельная проверка**
   - Реестр проверок в `tools/processforge.py` использует `ReleaseCommand("smoke_*", ...)` и не содержит `smoke_central_event_replay.py`.
   - Это видно из блока `release_test_commands(...)`: список состоит из `smoke_*`-скриптов, а `smoke_central_event_replay.py` отсутствует при поиске по имени.
   - Последствия: тест не выполняется стандартным `pf release-test`/`smoke-all`, не попадает в стандартный отчет релизной линзы.

2. **Нарушение принятой тестовой конвенции нейминг/расположения**
   - По контракту `release-test` ожидает отдельный smoke-скрипт с префиксом `smoke_` (см. список `ReleaseCommand`), тогда как целевой скрипт называется `smoke_central_event_replay.py`? *(именно отсутствует `smoke_` prefix в этом имени у релизного списка)*.
   - Он локализован в `tools/`, но не включён в релизный список.

3. **Внутренняя сторона частично соответствует требованиям**
   - Хорошо: нет argparse-поверхности публичного CLI в самом файле (строки 1–243 не используют `argparse`), что соответствует требованию дизайна об отсутствии public CLI surface (раздел теста 8).
   - Есть проверки на:
     - маршрутизацию/фильтрацию по `session_id`, `source_project_ref` и `codex-hooks`-потоку,
     - atomic/продолжение чекпоинта после частичных сбоев,
     - сценарии `repaired/present/unsupported_mapping/denied/failed` (строки ~83–230).
   - Но это представлено как самостоятельный `main`-smoke, а не набор явных фокус-тестов в форме 8 именованных unit-style тестов из дизайна.

## Рекомендация
- Ввести отдельный `ReleaseCommand` для `tools/smoke_central_event_replay.py` в `release_test_commands(...)` и/или переименовать/структурировать его под текущую принятую схему `smoke_*.py`, чтобы файл участвовал в release-валидации.
- Если планируется строгое совпадение с design-слайсом, перейти к явным `test_session_replay_*`-функциям (по сути 8 кейсов) и зафиксировать их через `smoke_*` конвенцию проекта.
