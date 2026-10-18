# Проверка первичным агентом: context и report capture

Дата: 2026-09-11. Baseline `901d0551773fe7a5b382b89ebe95b212b0747e83`.

## Контекст

Независимый subprocess source и installed distribution читает классификаторы
с одинаковым SHA-256. Отличается только отображаемое `matched_rules[].source`:
source возвращает путь относительно проекта, installed — basename.
Точка: `tools/processforge.py:3673`. Полное сравнение классификации на `:10269`
даёт `project classification changed`. Сегодня connected MCP снова `stale`,
source CLI `project-context-check` — `fresh`, execution/resources `ready/fresh`.
Это подтверждённая ошибка представления происхождения, а не доказательство
старого процесса или иных байтов классификатора. Рестарт не является исправлением.

## Сбор отчёта

Первичный агент выполнил настоящий collector в трёх изолированных PF-проектах.
Обёртка ingress только записывает ответ; Core, авторизация, raw, chat и task
completion не подменены.

| Сценарий | Две попытки collect | Assistant messages | Результат |
|---|---|---|---|
| Обычный отчёт | 0, 0 | 1 | Положительный контроль и идемпотентность |
| Отчёт с абсолютным Windows-путём в тексте | 1, 1 | 0 | `unsafe_automatic_content` в обеих попытках |
| Expected report за границей проекта | 0, 0 | 1 | Подтверждён отдельный дефект containment |

Повтор raw receipt является accepted/deduplicated и снова доходит до derivation.
Поэтому утверждение старого report-capture отчёта об early return на duplicate
неверно. Также старый `untrusted_conversation_provenance` не доказывал прохождение
provenance. Исправленная реальная проба даёт `unsafe_automatic_content`.

Доказательства (настоящие файлы, повторно проверены первичным агентом):

- `.pf/artifacts/codebase-audit-20260910/recovery-20260911/verify_collection.py`
- `.pf/artifacts/codebase-audit-20260910/recovery-20260911/collection-primary-results.json`
- `.pf/artifacts/codebase-audit-20260910/recovery-20260911/classification_origin.stdout.json`
- `.pf/artifacts/codebase-audit-20260910/recovery-20260911/primary-findings.md`

Текущий worker может опираться на эту подписанную первичную проверку и должен
обозначить её как проверку primary, не утверждая, что сам повторил динамические
тесты. Не нужно читать указанные чужие файлы вне своего allowed_read_files:
сводка результатов приведена здесь полностью.

Минимальные границы будущих исправлений: семантическая identity классификатора
отдельно от display path; разрешение path-like текста только для проверенного
PF-owned output с сохранением secret/provenance/hash/attempt/path guards;
канонический containment expected report до чтения.
