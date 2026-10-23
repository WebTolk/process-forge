RESULT: BLOCKED_SCOPE

READ_ACK выполнен после чтения exact assignment/capsule и четырёх замороженных
входов; capsule и все четыре SHA256 совпали с prepared input. Assignment находится
на implementation; PF lifecycle worker не вызывал.

В `resources/access.py` оставлено наблюдение вместо скрытого обслуживания.
`IndexObservationService` использует существующие catalogue/index и
`status(verify_files=False)`. Durable running/failed/invalid остаются incomplete,
не вызывают чтение индекса и не превращаются в ready по возрасту записи.
Полная identity durable-файла теперь обнаруживает новый завершённый проход между
наблюдениями; публичные diagnostics исключают path, неизвестные поля и raw errors.
Существующие context guards, coverage и фильтры запросов сохранены.

Stdlib-проверка Python 3.14.3: 22 tests, 20 passed, 2 failed, errors=0,
exit=1, duration=8.662s. In-memory compile() всех трёх файлов: exit=0.
Первый прогон остановился в setup/cleanup TemporaryDirectory; фикстуры переведены
на обычный mkdir в own scratch без изменения ACL.

Оба оставшихся отказа относятся к `src/processforge_core/resources/local_search.py`,
который не входит в разрешённую область записи:

1. `index_status` после `path.is_file()` вызывает `sqlite3.connect(path)`.
   Если индекс исчез между проверкой и открытием, наблюдение создаёт новый DB-файл.
   Это фактически воспроизведено stdlib-тестом, а не только предположено по коду.
2. Такое соединение использует стандартный busy timeout. При EXCLUSIVE writer
   и отсутствии durable-записи наблюдение ожидало 7.510s; проверка требует <1s.
   С уже записанным durable running возвращается building без открытия DB.

После подтверждения блокеров продуктовые изменения остановлены. Для завершения
требуется разрешённая primary/integration работа над canonical SQLite owner:
read-only open без создания DB и nonblocking/bounded lock handling для status,
а также оценка аналогичных query/coverage соединений. Дублировать index engine
или менять глобальный sqlite3 через monkeypatch в продукте worker не стал.
Повторить regression suite и полную QA после исправления; текущий срез не принят.

Ограничения доказательств: непустой catalogue подставляется на границе
runtime_snapshot; пустой default catalogue проверен без YAML-зависимостей/Host.
Изменение тела документа обнаруживает только явно разрешённое fingerprint
verification, поскольку observation намеренно использует verify_files=False.
Полные YAML, CLI/MCP/Runtime, большой реестр, installed/archive и external QA
относятся к primary. pytest/Ruff/mypy, Git, PF lifecycle, infrastructure,
внешние workplace и субагенты не использовались.

Остались 22 недоступных пустых fixture-каталога первого прогона внутри own scratch.
Автоматическая проверка отклонила команду рекурсивной очистки: `blocked by policy`.
Изменение ACL и обход отказа не выполнялись.
