RESULT: реализация вклада завершена, готова к проверкам primary. Родительский результат и alpha3 не объявляются завершёнными.

Изменены:

- `src/processforge_core/maintenance/journal_scan.py` — реализован `JournalScanService`.
- `tests/maintenance_scan/test_journal_scan.py` — 26 pytest-функций, 48 сценариев с параметризацией.
- Собственные план, evidence и `candidate-summary.json` в `.pf/artifacts/sqlite-journal-maintenance-alpha3-20261022/scan/exec-v3/`.
- `.pf/logs/sqlite-maintenance-alpha3-scan-v3-20261022.md`; воспроизводимые stdlib-проверки в разрешённом scratch.

Сохранён API:

```python
discover(project, workplace) -> tuple[Path, list[JournalSource]]
rows(sources, project, report, *, skip_invalid=False, quarantine_dir=None)
preflight(project, workplace, *, skip_invalid=False, evidence_dir=None)
```

Переиспользованы существующие discovery, project filtering и native identity primitives. Добавлены строгий UTF-8/JSON, раздельные счётчики, точный карантин NUL/CRLF/последней строки без newline, provenance с line/offset/length/SHA256, проверяемый manifest и отказ от перезаписи конфликтующих evidence. Дедупликация использует временную SQLite-базу; конфликты ID блокируют обработку независимо от `skip_invalid`. Проверяются полные source hashes и signatures. Обратных вызовов Main/Host нет.

Выполнена команда:

```text
python -I -B .pf/tmp/sqlite-maintenance-scan-v3-20261022/local_checks.py
```

Python 3.14.3, exit **0**: **11 passed, 1 skipped** — создание symlink недоступно. Проверены карантин, явный skip, повторное использование evidence, tamper, дедупликация, native-конфликты, discovery/preflight, дрейф и закрытие индекса. `ast.parse` обоих файлов прошёл. Хеши кандидата указаны в `candidate-summary.json`.

Pytest, Ruff, format, mypy, coverage и security **не запускались исполнителем**; их выполняет primary. Метаданные карантина растут с числом повреждённых строк; строки читаются целиком. Потребитель `rows` должен исчерпать iterator, учитывать `blocked` и сверять source manifests между проходами.

READ_ACK и RESULT отправлены реальными progress-сообщениями. Чужие файлы, Main, contracts, version, Git, PF lifecycle и инфраструктура не изменялись.