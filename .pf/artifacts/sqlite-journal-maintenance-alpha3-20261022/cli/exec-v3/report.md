**RESULT: CLI-вклад реализован; обязательная QA остаётся за primary.**

READ_ACK выполнен: локальные Python excerpts, provenance, архитектура, handoff и contracts прочитаны; SHA256 совпали с prepared input.

Добавлены:

- `tools/pf_cli/parsers/journal_maintenance.py`
- `tools/pf_cli/commands/journal_maintenance.py`
- `tests/maintenance_cli/conftest.py`
- `tests/maintenance_cli/test_journal_maintenance.py`
- `docs/concepts/sqlite-journal-maintenance.md`
- `docs/ru/concepts/sqlite-journal-maintenance.md`

API: `register_journal_maintenance(add_parser, *, execute)` и холодный `JournalMaintenanceCommand(...).execute(args) -> int`. Пять операций вызывают реальные Core owners без Main/Host callbacks. Обработанные операции возвращают один JSON-объект: успех/план — `0`, отказ/ошибка — `1`; синтаксис argparse — `2`.

Финальная локальная проверка:

`python -B .pf/tmp/sqlite-maintenance-cli-v3-20261022/check_local.py --registered`

Python **3.14.3**, **24 теста прошли**, exit **0**, **9.323 с**. Проверены реальные WAL backup/restore, tamper, запрет перезаписи, точные NUL-байты/хеш/смещение карантина, неизменность источников, явный skip, конфликт identity и повтор без дублей. Четыре теста полного CLI прошли после регистрации primary.

Хеши кандидата и протокол находятся в `cli/exec-v3/changed-files.json` и `local-checks.txt` внутри выделенного каталога артефактов.

Main/contracts/version не изменялись executor. Зарегистрированные pytest/Ruff/format/mypy/coverage/security, review и приёмка alpha3 не заявляются выполненными. После первоначального sandbox-отказа сохранены 13 недоступных пустых fixture-каталогов в собственном scratch; успешные fixtures очищены.