# Передача primary: проверки и границы evidence

## Фактически выполнено

```text
python -B .pf/tmp/context-index-alpha4-integration-20261023/run-stdlib.py
exit 0
23 tests; failures=0; errors=0; skips=0
Python 3.14.3; SQLite 3.50.4
AST/compile: 5 owned Python files
```

Результат на 2026-10-23T05:43:24Z: `stdlib-results.json`. Время suite 38.742522 с. Runner использует stdlib unittest и доступные зависимости продукта; это не запуск зарегистрированного pytest/Ruff/mypy. Собственные UUID fixtures удаляются только после проверки resolved containment.

Проверены:

- Первый и повторный реальный refresh/init/repair при missing/stale/durable-running index и отсутствии обращения к App Server; нет build/queue/wait/launch, index/state bytes не меняются.
- Реальный parser нового manual CLI, apply refusal до эффектов, canonical owner для CLI и явно вызванного холодного job; scoped refresh/rebuild/tick сохраняют выбранные источники.
- R4 dirty/deferred trigger map и реальное mark-dirty без индексации.
- Независимый отказ при отсутствующем required platform contract даже при свежем поиске.
- Разрешённые project результаты, counts/pagination, empty selection и live snapshot revocation; metadata-only bodies не раскрываются.
- Work not-in-work/not-in-stage, invalid query, live revocation, metadata drift и same-size/same-mtime material change. Work identity admission здесь изолирован на prevalidated seam, не проверен заново.
- Invalid query/offset при unavailable/fresh/stale index, corrupt result JSON и corrupt persisted scope metadata; ошибки не превращаются в успешные пустые ответы.
- Реальный writer barrier, bounded second-writer refusal, exclusive SQLite lock, abrupt child-process exit и последующее восстановление через canonical cold job с сохранением history.
- Runtime не импортирует/не регистрирует future job; construction не создаёт thread/timer и не вызывает maintenance.

## Замеры

67 зарегистрированных ресурсов, 1538 fulltext-файлов, 3379259 source bytes с учётом metadata-only body. Счётчик — attempted `Path.open` в режиме чтения; byte totals — размеры файлов при open, не физический дисковый I/O. Время включает instrumentation и fixture configuration.

| Операция | Секунды | Открытия тел: выбранные / остальные | Открытия metadata: catalogue / project-runtime |
| --- | ---: | ---: | ---: |
| Первый refresh, индекс отсутствует | 0.847392 | 0 / 0 | 84 / 300 |
| Явное initial maintenance | 5.601686 | 1 / 1537 | 69 / 207 |
| Повторный refresh, индекс готов | 1.003536 | 0 / 0 | 99 / 380 |
| Явный verified no-op maintenance | 2.136620 | 1 / 1537 | 69 / 207 |
| Проверка выбранного Work material | 0.005687 | 1 / 0 | 0 / 0 |

Refresh продолжает читать текущие structured sources/metadata. Отдельная проверка материала читает выбранный файл даже с `include_content=False`; это обязательная material validation, не индексация workplace. Git baseline не запускался, speedup/production benchmark не заявляется.

## Требуется от primary

- Зарегистрированный `python-pytest` для всего `tests/context_index_separation/`, включая проверку collection с новым bootstrap.
- Registered Ruff lint/format и mypy затронутой области; coverage/Bandit по pinned QA policy. Внешние команды/установки worker не запускал.
- Полный изменённый MCP stdio smoke и полный snapshot-composition smoke; локально выполнены только три изменённые policy-проверки второго smoke. Остальные existing smokes выбирает primary по общей risk map.
- Независимое review после всех implementation corrections; candidate/archive/installed/connected-host qualification и delivery принадлежат primary.

Исторический observation BLOCKED_SCOPE не переименован в pass; его readonly repair и результаты primary отделены от собственных проверок. Ограничение существующего engine, который пропускает некоторые ошибки чтения source files, остаётся residual maintenance report и требует решения primary/reviewer; этот worker не менял engine.

Автоматическая проверка отклонила удаление начального own-scratch каталога с причиной `blocked by policy`; каталог сохранён, ACL не менялись. Это ограничение очистки, не отказ функциональных тестов.
