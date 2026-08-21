# Отчёт по корректировке релизных гейтов

## Результат
Задание выполнено на уровне текущего кода: требуемые префлайты и smoke уже присутствуют, дополнительная доработка файлов в этой итерации не потребовалась.

## Проверено

- В `tools/processforge.py` `release-pack` уже содержит префлайт `ReleaseCommand("public cleanliness", validate-public-cleanliness.py)` на строке ~6564 и `ReleaseCommand("checksum", validate-process-forge-checksums.py --check)` на строке ~6587.
- В `release-pack` уже зарегистрированы критические smoke для ядра/ingress/replay: `smoke_central_event_ingress` (6567), `smoke_central_event_replay` (6593), `smoke_conversation_completeness` (6594), а также `smoke_process_supervisor_tick` (6595).
- Для `release-test` preflight уже явно перечислены `public cleanliness`, `checksum inventory`, `smoke_central_event_ingress`, `smoke_conversation_completeness`, `smoke_central_event_replay` (строки 7079, 7361-7366).
- В `tools/validate-public-cleanliness.py` сохранён механизм сохранения security-fixture через marker: `public-cleanliness: allow-private-path-fixture` (строки 36, 46-50 и далее в обработке AST).
- В `tools/smoke_public_cleanliness.py` есть подтверждающий regression smoke с маркером в безопасном fixture и проверкой отказа для немаркированного Python-литерала.
- `.processforge-releaseignore` содержит обязательные записи по `docs`, runtime/private структурам и служебным каталогам (строки 1-25 файла).
- Публичные доки уже отражают текущую архитектуру: raw-first/ingress/replay/conversation path, в т.ч. в `docs/concepts/hooks-events.md`, `docs/concepts/process-events.md`, `docs/concepts/runtime-model.md`, `docs/concepts/processforge-events.md` и русской версии `docs/ru/concepts/hooks-events.md`, `docs/ru/concepts/runtime-model.md`, `docs/ru/concepts/processforge-events.md`.

## Существующие ограничения

- Как и в предыдущем гейт-репорте, полная `release-test` трасса заканчивается на ранее существующем `doctor-project` сбое из‑за отсутствия onboarding артефактов (`.pf/assignments/first-assignment.yaml` и эквивалентной инициализации).
- В текущей сессии изменений в файлы не применялось, так как их состояние уже соответствует целевым правкам согласно текущим артефактам.