# Отчёт: project-init local search MCP — commit и push

Дата: 2026-08-21

## Публикация

- Ветка: `dev`.
- Commit: `412e3df` — `feat: add project init local FTS search MCP`.
- Push: успешно отправлен в `origin/dev`.

## Содержимое среза

- Общий Core service для статуса, инициализации и repair проекта.
- Локальный SQLite FTS5 поиск только по snapshot-authorized ресурсам, с
  `limit`, `limitstart` и `offset`.
- MCP/CLI/session integration, containment private path refs, template search и
  stage obligations.
- Acceptance/release smoke, доказательства и независимые review.
- Исправления release hygiene: Windows read-only cleanup, schema/output paths,
  capability-waiver smoke и lifecycle self-contained distribution после
  удаления `.pf/runtime`.

## Проверки

- `python tools/smoke_doctor_project_capability_waiver.py` — PASS.
- Schema validation и checksum inventory — PASS.
- `python bin/pf.py release-test --root . --only "clean release artifacts"
  --only "doctor-project" --fail-fast` — PASS.
- Полный `release-test --public --fail-fast` в изолированной копии —
  `RESULT: PASS with warnings` за 718.82 s. Единственное предупреждение:
  `git diff --check` пропущен, поскольку изолированная копия намеренно не
  содержит `.git`.

## Известные внешние границы

- Реальный live `pf.search` вызов из Codex блокируется политикой approval
  `never`; registration/visibility подтверждены отдельно.
- Новый ZIP в этом запуске не создавался: до commit рабочее дерево было
  намеренно dirty. Существующие archive-файлы не перезаписывались.

## Примечание

Этот отчёт создан после commit и push по прямой последовательности запроса и
потому не входит в commit `412e3df`.
