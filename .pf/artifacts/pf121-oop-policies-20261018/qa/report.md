# QA: classifier и artifact policies

Статус: **passed — 137/137 проверок**. Расхождений с frozen baseline и блокирующих замечаний не обнаружено.

## Идентичность и допуск

- Project: `process-forge`.
- Run: `garage-p121-policies-qa-after-implementation-and-primary-fixture-based-s`.
- Assignment: `p121-policies-qa-after-implementation-and-primary-fixture-based-smoke-ex`.
- Context: `p121-policies-qa-after-implementation-and-primary-fixture-based-smoke-ex-capsule`.
- Точный Work проверен существующим source CLI: стадия `implementation`, context `valid`, execution readiness `ready`, blockers отсутствуют.
- Хеши capsule, snapshot и всех пяти prepared sources совпали с входом. Metadata-only ресурсы не читались.

## Результаты

| Группа | Успешно / всего |
| --- | ---: |
| Classifier: формы данных, условия, all/any precedence | 37/37 |
| Classifier: short circuit и native errors | 8/8 |
| Matcher: пути, basename, backslash, платформенный fnmatch | 22/22 |
| Artifact declarations: scalar/list/dict, IDs, дубликаты | 24/24 |
| Produced artifacts: stages и string-list semantics | 13/13 |
| Порядок truthiness/str и исключений | 6/6 |
| AST parity и неизменность исходного текста `rel` | 9/9 |
| Миграция определений и callers | 7/7 |
| Direct/copied Core и зависимости владельцев | 4/4 |
| Целостность входов, Work и исходников | 7/7 |
| **Всего** | **137/137** |

Выполнены 109 сравнений поведения с frozen baseline и отдельная проверка стандартного платформенного `fnmatch`. Сохранены приоритет списка `all`, включая пустой список, short circuit, полный путь и basename, нормализация обратных слешей, различия scalar/list/dict, truthiness ID, устранение дубликатов и порядок преобразований.

В 20 случаях совпали типы и сообщения ожидаемых исключений: `AttributeError`, `TypeError`, `ValueError`. Проверки наблюдаемого порядка подтвердили truthiness перед преобразованием ID, повторный вызов `str` для элементов списка, сохранение пробелов и прежний порядок ошибок.

Обычное создание экземпляров и вызовы публичных методов успешны в отдельных изолированных процессах для исходного и скопированного Core. CLI/Host не импортировались; все загруженные модули Core происходили из выбранного дерева. Существующий package initializer загружает `process_catalog.service`; сами новые владельцы его не импортируют.

Все исходные consumer-вызовы сверены с baseline-коммитом: оба classifier callers, семь artifact-вызовов и два shared matcher callers соответствуют ожидаемой миграции. Пять устаревших helper names отсутствуют в `src` и `tools`; старое определение matcher удалено из монолита. Канонический `path_matches_pattern` сохранён в общем владельце и callers. Генерические `as_list`/`string_list` остаются в монолите.

## Smoke evidence и source_sha256

Receipt primary подтверждает **7/7 успешных smokes**. Его source hashes совпадают с проверенными файлами и оставались неизменными до окончания QA. Smokes повторно не запускались.

| Файл | SHA-256 |
| --- | --- |
| `tools/processforge.py` | `ebd867d78eca02239112f8d2eee4b027b5d58509d1a9784453f6b2e22433a2ac` |
| `src/processforge_core/project/classification.py` | `22b8865a70a03390d379afed9853afb1bc12f0ee831875e91d6ad3ec63d10b00` |
| `src/processforge_core/common/paths.py` | `19b5bfecb8506f68a5efe7e5dcca34851b3b638bc14c83cabe89aac324f9ae56` |
| `src/processforge_core/process_catalog/artifacts.py` | `7ab9b30545e08e4db688760be8099ccae707c2ebd6621492b65d1449ece8a2a6` |

## Evidence и журнал

- `.pf/artifacts/pf121-oop-policies-20261018/qa/results.json` — подробные результаты, исключения, imports, identity и хеши. SHA-256: `7ededc4ab710429fc3b123d7480a4def660f2c01ebf8e32b49d6b61ac90f14d0`.
- `.pf/artifacts/pf121-oop-policies-20261018/qa/work-state.json` — точное состояние Work.
- `.pf/artifacts/pf121-oop-policies-20261018/primary/baseline-functions.json` — frozen baseline.
- `.pf/artifacts/pf121-oop-policies-20261018/primary/smoke-results.json` — receipt primary.
- `.pf/tmp/p121-policies/qa/parity.py` и `.pf/tmp/p121-policies/qa/verify-evidence.py` — ограниченные harness scripts, сохранённые как evidence.

2026-10-18, worker-p121-policies-qa, UTC:

- **17:48:31:** начаты parity-проверки; продуктовые записи отсутствуют.
- **17:49:49:** завершены дополнительные проверки callers и зависимостей. В сборщике evidence исправлены формирование имени capsule-файла и сравнение LF Git bytes с frozen CRLF working-file hash. Parity и smokes повторно не запускались.
- **17:50:33:** итог 137/137; исходники стабильны. Временная копия Core удалена, harness scripts оставлены как evidence.

## Ограничения и передача

В primary inventory smoke пропущены две symlink-проверки из-за недоступности symlink. Их успешность не заявляется. Приёмка на другой платформе, release/archive/install, Runtime и фактический Host не проверялись.

Продукт и постоянные тесты не изменялись. Git mutations, remote access, infrastructure changes, nested agents, context rebuild и lifecycle transitions не выполнялись. Дальнейшие независимый review и native transitions остаются за main.