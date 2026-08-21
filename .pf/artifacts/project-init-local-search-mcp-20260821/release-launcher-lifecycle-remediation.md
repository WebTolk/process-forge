# Исправление lifecycle release cleanup и doctor

Дата: 2026-08-21

## Дефект

`release-test` очищал private `.pf/runtime`, а затем `doctor-project` требовал
`.pf/runtime/bin/pf.py` даже в self-contained checkout ProcessForge, который
уже содержит `bin/pf.py` и core tools.

## Исправление

Для отсутствующего launcher `doctor-project` возвращает WARN только если
`looks_like_processforge_distribution(project_root)` подтверждает
self-contained distribution. Обычный linked-проект и далее получает FAIL с
инструкцией выполнить onboarding. Cleanup `.pf/runtime` не ослаблен.

## Проверка

- `python bin/pf.py clean --root . --release` — PASS;
- `python bin/pf.py doctor-project --project-root .` — PASS с ожидаемым WARN;
- `python bin/pf.py release-test --root . --only "clean release artifacts"
  --only "doctor-project" --fail-fast` — PASS;
- `python -m py_compile tools/processforge.py` и `git diff --check` — PASS.

Независимый review: `.pf/reviews/project-init-local-search-mcp-release-launcher-lifecycle-review-20260821.md`.
