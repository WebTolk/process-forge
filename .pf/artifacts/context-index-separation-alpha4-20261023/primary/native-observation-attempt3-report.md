RESULT: BLOCKED_SCOPE

Assignment: `alpha4-native-observation-contribution-under-frozen-1-1-4-architecture-i`, attempt 3. Срез не готов к приёмке.

READ_ACK: прочитаны exact assignment/capsule, замороженные architecture/domain, Python/OOP guidance и Python excerpts. Проверенные SHA256 совпали с prepared input.

Изменённые файлы и API:

- `src/processforge_core/resources/access.py`: `ResourceSearchService.readiness`, `_readiness`, `search` используют наблюдение; сохранены context guards, coverage, пагинация и фильтрация ресурсов.
- `src/processforge_core/resources/index_observation.py`: `maintenance_state_path`, `IndexObservationService.observe`; добавлены сравнение identity durable-записи между чтениями и allowlist публичных диагностических полей. Running/failed/invalid не объявляются ready.
- `tests/context_index_separation/test_observation.py`: добавлены 22 проверки stdlib unittest.
- `.pf/logs/context-index-alpha4-observation-20261023.md`: обновлён журнал.
- В `.pf/artifacts/context-index-separation-alpha4-20261023/observation/` добавлены `changed-files.md`, `change-summary.md`, `checks.json`, `unittest.txt`.

Фактические проверки: Python 3.14.3; из собственного scratch выполнено `python -I -S -B ../../../tests/context_index_separation/test_observation.py`. Результат: **20 passed, 2 failed, errors=0**, exit=1, 8,662 с. Компиляция трёх файлов через `compile()` в памяти прошла, exit=0.

Блокеры воспроизведены в существующем `src/processforge_core/resources/local_search.py:index_status`:

1. Между `path.is_file()` и `sqlite3.connect(path)` индекс удаляется; наблюдение создаёт новый DB-файл.
2. При EXCLUSIVE-блокировке SQLite и отсутствии durable-записи наблюдение ожидало **7,510 с**. При durable running проверка проходит без открытия DB.

`local_search.py` не входит в разрешённую область записи. После подтверждения блокеров продуктовые правки остановлены. Для завершения primary требуется разрешённая правка канонического SQLite owner: открытие без создания файла и неблокирующее чтение, затем повтор тестов и полной QA.

Ограничения: непустой catalogue подставляется на границе `runtime_snapshot`; проверен также пустой default catalogue. Observation намеренно не перепроверяет содержимое документов. Внешние QA, Git, PF lifecycle, инфраструктура, внешние workplace и субагенты не использовались.

Автоматическая проверка отклонила рекурсивную очистку scratch с причиной `blocked by policy`. В собственном scratch остались 22 каталога первого прогона; ACL не менялись.