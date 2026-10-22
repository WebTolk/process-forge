**RESULT: W1 реализован и готов к assurance primary.**

Добавлены:

- `src/processforge_core/maintenance/backup.py`
- `tests/maintenance_backup/test_backup.py`

API холодного `SQLiteBackupService(*, timeout: float = 10.0)`:

```python
create(source: Path, bundle: Path) -> JsonObject
verify(bundle: Path) -> JsonObject
restore(bundle: Path, destination: Path) -> JsonObject
```

Реализованы WAL-aware `Connection.backup` с фиксированным read snapshot, эксклюзивный bundle, строгая проверка manifest/member paths, повторные SHA256-проверки, `integrity_check`, эксклюзивное восстановление, дедлайны и очистка собственных файлов по identity. Ошибки возвращаются через `MaintenanceError.code`. Успешные JSON-отчёты содержат статус, расположение результата, хеши, размер и SQLite metadata.

Локальная проверка:

```text
python -B .pf/artifacts/sqlite-journal-maintenance-alpha3-20261022/backup/exec-v3/local-checks-driver.py
```

Python 3.14.3, SQLite 3.50.4: **39 тестов, 34 прошли, 5 пропущены, failures=0, errors=0, exit=0**. Проверены WAL, конкурентный commit, конкуренция create/restore, tamper, повреждение БД, таймауты SQLite и очистка после отказов.

Команда, полный вывод и SHA256 проверенных файлов находятся в `backup/exec-v3/local-checks-final.json` внутри выделенного artifact namespace. Там же находятся `changed-files.json`, `change-summary.md`, драйвер и промежуточные evidence. Журнал: `.pf/logs/sqlite-maintenance-alpha3-backup-v3-20261022.md`.

Ограничения:

- SQLite при `mode=ro` может создать WAL/SHM coordination sidecars; абсолютная неизменность файловой системы источника не гарантируется.
- Пять symlink-тестов пропущены из-за прав sandbox; реальные symlink/junction-сценарии требуют проверки primary.
- SHA256 не подтверждает аутентичность согласованно заменённых БД и manifest.
- В собственном scratch остался 31 недоступный каталог первоначальных fixtures; ACL не изменялись.
- Зарегистрированные pytest/Ruff/format/mypy/coverage/security не запускались. Assurance, интеграция и приёмка alpha3 остаются за primary.