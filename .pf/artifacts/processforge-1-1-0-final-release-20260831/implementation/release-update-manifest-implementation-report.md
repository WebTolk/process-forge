# Реализация release/update-контракта ProcessForge 1.1.0

## Результат

- Каноническая версия выпуска — `1.1.0`; `1.2.0` и `1.2.1` не входят в stable-канал.
- Production update-site переведён на
  `release/updates/processforge-stable.json` в репозитории WebTolk/process-forge.
- Stable-манифест будет ссылаться только на неизменяемые GitHub Release assets
  тега `v1.1.0` и получит SHA-256/размер из финального архива.
- Исторический sidecar хранится отдельно в
  `release/1.1.0/processforge-1.1.0.manifest.json`; каталог `release/` не входит
  в состав ZIP.
- Добавлены исполняемые проверки схемы, production URL, archive boundary,
  Git/tag provenance и соответствия stable-манифеста архиву.
- Миграция переименована в `updates/migrations/1.1.0-stable-release.md`; для
  перехода с `1.0.2` обязательная миграция проекта не требуется.

## Выполненные проверки

- `python -m py_compile ...` для изменённых Python-файлов — PASS.
- `smoke_no_production_example_update_urls.py` — PASS.
- четыре документационных smoke-контракта — PASS.
- `smoke_project_init_codex_integration.py` — PASS.
- `smoke_first_run.py` — PASS.
- `smoke_project_init_acceptance.py` — PASS.

Финальные SHA-256, stable JSON, tag provenance и extracted-archive проверки
выполняются на стадии release-delivery после фиксации точного source commit.
