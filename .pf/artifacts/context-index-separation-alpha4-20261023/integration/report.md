READ_ACK: прочитаны prepared input, R2/R3/R4, Python excerpts/provenance, OOP contracts, текущие исходники, отчёты observation/maintenance/cold-job и primary QA handoff.

Assignment: `alpha4-fourth-native-contributor-integration-tests-and-en-ru-docs-after`, attempt 1.

Первым изменением добавлен `tests/context_index_separation/conftest.py` с bootstrap `tools`/`src`.

Созданы `test_integration.py` и `test_backend_contract.py`. Обновлены два owned smoke: `smoke_project_init_local_search_mcp.py` и `smoke_resource_search_snapshot_composition.py`. Обновлены четыре EN/RU concept-документа о project context и resource search. Продуктовая реализация не изменялась.

Добавлены проверки:

- Первый и повторный refresh/init/repair при missing/stale/running index без maintenance, ожидания или обращения к App Server.
- Новый manual CLI и холодный job вызывают общий owner; scoped refresh/rebuild/tick сохраняют выборку проекта.
- R4 mutation triggers оставляют явное обслуживание отдельно от mark-dirty.
- Обязательный context resource блокирует refresh независимо от готовности поиска.
- Project/Work access, отзыв доступа, ограничения этапа, counts/pagination и metadata-only policy.
- Invalid query/offset, повреждённые metadata, изменение материала при одинаковых размере и mtime.
- Конкуренция readers/writers, bounded busy refusal, аварийный выход процесса и явное восстановление с сохранением history.
- Отсутствие регистрации future job и поискового таймера в Runtime.

Фактический локальный запуск:

```text
python -B .pf/tmp/context-index-alpha4-integration-20261023/run-stdlib.py
exit 0
23 tests: 20 новых + 3 policy smoke
failures/errors/skips: 0/0/0
Python 3.14.3; SQLite 3.50.4
38.742522 с
```

AST-разбор и компиляция пяти изменённых Python-файлов успешны. Проверка итоговых байтов подтвердила совпадение SHA256 всех девяти source/doc-файлов с успешным прогоном. Evidence: `integration/stdlib-results.json` и `integration/final-verification.json`.

Замеры выполнены на собственном fixture: 67 ресурсов, 1538 fulltext-файлов, 3 379 259 source bytes с учётом metadata-only body.

| Операция | Секунды | Открытия тел документов | Открытия metadata |
| --- | ---: | ---: | ---: |
| Первый refresh, индекс отсутствует | 0.847392 | 0 | 384 |
| Явное initial maintenance | 5.601686 | 1538 | 276 |
| Повторный refresh, индекс готов | 1.003536 | 0 | 479 |
| Verified no-op maintenance | 2.136620 | 1538 | 276 |
| Проверка выбранного Work material | 0.005687 | 1 | 0 |

Счётчики отражают attempted `Path.open` в режиме чтения, не физический дисковый I/O. Refresh продолжает читать structured sources и metadata. Отдельная проверка материала прочитала только выбранный файл; это material validation, а не индексация workplace. Времена включают instrumentation. Baseline из Git не запускался; ускорение относительно прежней версии не заявляется.

Документация описывает приватное workplace-хранилище SQLite FTS5, независимые context/search/coverage states, explicit workplace authorization и общий maintenance component. Scheduler, DAL, другие SQL/vector backends и RAG обозначены как будущие задачи.

Границы доказательства: Main использует fixture distribution root; broad doctor, agent entry и optional host integration изолированы. Work identity admission подставлен на prevalidated seam; текущие access/material checks реальные. Зарегистрированные pytest/Ruff/format/mypy, полные smokes и независимое review остаются за primary. Archive/installed/connected-host и POSIX acceptance не подтверждены. Унаследованные пропуски некоторых source-read errors в engine не устранялись.

Два промежуточных fixture-сбоя исправлены; первоначальные результаты сохранены. Git, PF lifecycle, инфраструктура, внешняя индексация и субагенты не использовались.

RESULT: ready_for_review — разрешённая реализация тестов и документации завершена; обязательная общая QA и приёмка остаются за primary.

Автоматическая проверка отклонила удаление начального собственного scratch-каталога с причиной `blocked by policy`. Каталог сохранён; ACL не менялись.