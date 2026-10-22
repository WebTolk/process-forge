**RESULT: реализация вклада завершена; QA и интеграционная приёмка primary ожидаются.**

Assignment: `a3-file-service-20261022-native-file-only-contribution-implement-complet`, attempt 1. READ_ACK отправлен после чтения фактических frozen inputs; их проверенные SHA256 совпадают.

Изменены:

- `src/processforge_core/maintenance/journals.py` — сервис с injected BackupPort/JournalScanPort и cold defaults.
- `tools/migrate-hook-journals.py` — тонкий delegate, сохранены flags/JSON/exit mapping; добавлен `--evidence-dir`.
- `tests/maintenance_service/test_journals.py` — 23 pytest-функции, 28 cases.

API:

```python
migrate(
    project_root: Path,
    workplace: Path,
    *,
    apply: bool = False,
    skip_invalid: bool = False,
    evidence_dir: Path | None = None,
) -> JsonObject
```

Сервис выполняет preflight/quarantine до импорта, проверенные backups до DB mutation, импорт через существующие owners и транзакции, проверку source drift, integrity/counts/ID/содержимого и replay без вставок. При отказе сохраняет recovery evidence и возвращает barriers существующим pinned DB; исчезнувшие базы не создаёт.

На итоговых стабильных байтах прошли compile трёх файлов и оба локальных stdlib-checks: `local_check.py`, `failure_check.py`, exit 0. Среда: Python 3.14.3, SQLite 3.50.4. Проверены events/raw import, NUL quarantine, повтор, backups, partial commit/retry, batch recovery, drift, semantic tamper, destination replacement/disappearance и legacy CLI.

Команды, результаты и полные hashes находятся в `.pf/artifacts/sqlite-journal-maintenance-alpha3-20261022/service/exec-v3/local-checks-v2.json`.

Pytest, Ruff, format, mypy, coverage/security остаются за primary и здесь не запускались. Старому migration smoke требуется адаптация внутренних patch targets к owning scanner/journal classes.

Финализация двух DB использует отдельные commits. Жёсткое завершение процесса между ними требует проверки evidence и явного retry. Приёмка родительского результата и выпуск alpha3 ожидаются.