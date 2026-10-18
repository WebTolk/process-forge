**Независимое review p121-policies: принято в пределах source-only. Блокирующих замечаний нет.**

Дата: 2026-10-18. Роль: worker-p121-policies-review.

- Project: `process-forge`.
- Run: `garage-p121-policies-review-independent-clean-context-source-review-afte`.
- Assignment: `p121-policies-review-independent-clean-context-source-review-after-imple`.
- Context: `p121-policies-review-independent-clean-context-source-review-after-imple-capsule`.
- Baseline: `c75797d9a2d206c3ce5b3b6c5968fed092cbcd1e`.

Точный Work проверен существующим source CLI с явными selectors: стадия `implementation`, context `valid`, execution readiness `ready`, blockers отсутствуют. Capsule, snapshot и все девять обязательных prepared sources соответствуют переданным SHA256. Обязательные inline-материалы прочитаны; тела metadata-only ресурсов не открывались.

Рассмотрены фактические исходники семи продуктовых файлов, ограниченный локальный Git diff, frozen algorithms, подробные QA results, harness scripts, primary smoke receipt и inventory receipt. Для чтения символов использована Serena; дополнительные проверки выполняли только чтение и структурное сравнение исходников.

**Результаты проверки исходников**

| Область | Заключение |
| --- | --- |
| Classifier | `ProjectClassifierRulePolicy` владеет алгоритмом. Список `all` сохраняет приоритет над `any`, включая пустой список с результатом `False`. Оба чтения `when.get` остаются до выбора ветви; генераторы сохраняют short circuit. Проверки формы данных, `exists.strip()` и нормализация слешей соответствуют baseline. |
| Общий matcher | Сохранены `path.replace`, предварительное вычисление `Path(normalized).name`, затем `fnmatch.fnmatch` полного пути и basename через `or`. Дополнительной нормализации pattern, `fnmatchcase` или изменения платформенной семантики нет. `rel` не изменён. |
| Artifact declarations | `ProcessArtifactDeclarationPolicy` сохраняет различия dict/list, truthiness ID, устранение дубликатов, порядок групп и преобразований. Приватный `_as_list` повторяет эффективное последнее определение монолита: любой non-list даёт `[]`. Отличающийся helper из `process_catalog.service` не используется. |
| Строки и ошибки | `_string_list` сохраняет фильтрацию через первый `str(item)`, повторный `str(item)` для включённого элемента и пробелы результата. Поведение строк через запятую и внешний `str` в `produced_ids` сохранены. Новых catches, coercion или переупорядочивания native errors нет. |
| Неизвестные поля | Алгоритмы читают прежние ключи, не обходят неизвестные поля и не изменяют входные документы. Новая валидация не добавлена. |

Все восемь frozen helper bodies структурно совпали с соответствующими определениями baseline-коммита, включая последнее `as_list`. Diff и сравнение AST подтвердили: все 979 оставшихся функций монолита соответствуют baseline после только предусмотренной замены вызовов.

Полнота миграции подтверждена:

- оба classifier consumers — `inactive_official_classifier_hints` и `classify_project` — вызывают owning policy;
- семь artifact-вызовов в authoring validation, process contract validation и builtin catalog report переведены на owning policy;
- `detection_group_matches` и `platform_detection_matches` используют импортированный общий matcher;
- пять устаревших helper names отсутствуют в `src` и `tools`; прежнее определение matcher удалено из монолита;
- generic `as_list` и `string_list` сохранены для остальных потребителей.

Новые владельцы — обычные stateless objects без callback, provider, deferred import или пути исполнения обратно в монолит. Они не вводят I/O, кэширование, решения о доступе или lifecycle authority. Существующие package initializers, bootstrap и catalog service не изменены. Eager import `process_catalog.service` через существующий initializer учтён; новые policy его не используют.

**Документация и inventory**

EN/RU справки соответствуют фактическим владельцам, методам и consumers. Границы оставшихся legacy-обязанностей указаны корректно; полной миграции или завершения OOP-эпиков не заявлено.

Все шесть затронутых inventory hashes независимо сверены с текущими файлами через существующие `released_content`/`sha256`. Различие raw CRLF hash монолита и release LF hash объясняется штатной нормализацией. Остальные 1313 строк совпадают с baseline по содержимому; их текущий raw hash совпадает с receipt. Три известных посторонних расхождения повторно не валидировались. Ограниченный `git diff --check` прошёл.

**Проверка evidence**

Подробный `qa/results.json` имеет ожидаемый SHA256 `7ededc4ab710429fc3b123d7480a4def660f2c01ebf8e32b49d6b61ac90f14d0`. Он подтверждает 137/137 проверок, включая 20 случаев native exceptions. Просмотр harness scripts подтверждает проверки наблюдаемого порядка преобразований и изолированные direct/copied Core imports.

Текущие raw source hashes совпали с QA и primary smoke receipt:

| Файл | SHA256 |
| --- | --- |
| `tools/processforge.py` | `ebd867d78eca02239112f8d2eee4b027b5d58509d1a9784453f6b2e22433a2ac` |
| `src/processforge_core/project/classification.py` | `22b8865a70a03390d379afed9853afb1bc12f0ee831875e91d6ad3ec63d10b00` |
| `src/processforge_core/common/paths.py` | `19b5bfecb8506f68a5efe7e5dcca34851b3b638bc14c83cabe89aac324f9ae56` |
| `src/processforge_core/process_catalog/artifacts.py` | `7ab9b30545e08e4db688760be8099ccae707c2ebd6621492b65d1449ece8a2a6` |

Primary receipt подтверждает 7/7 focused smokes. Исправление распознавания описательных PASS-сообщений основано на сохранённом выводе с нулевыми exit codes. Повторного запуска smokes, parity corpus, fixture или полных тестов в этом review не было.

**Ограничения и передача**

Приёмка относится к рассмотренным исходникам и соответствующим evidence. Две symlink-проверки существующего inventory smoke пропущены. Исполнение на другой платформе, архив, установка, Runtime и подключённый Host не квалифицированы. Commit, dual-remote delivery и native transitions этим отчётом не подтверждаются и остаются за main.

Продуктовые файлы и report file не записывались. Git index/history, remotes, инфраструктура и lifecycle state не изменялись; новые Work, context rebuild и вложенные агенты не запускались.