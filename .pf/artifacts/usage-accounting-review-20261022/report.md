**Вердикт: FAIL — два неустранённых замечания P2.**

Assignment: `usage-accounting-review-20261022`, attempt `1`; run: `usage-accounting-workers-20261022`; context: `usage-accounting-review-20261022-capsule`. SHA-256 капсулы совпал с prepared input. Все 17 файлов кандидата совпали с `changed-files.json` до и после проверки. Продуктовые файлы не изменялись.

**Замечания**

1. **P2 — неверный тип timestamp нарушает обработку malformed input и сохранение валидного префикса.**

   Места: `src/processforge_core/accounting/binding.py:20`, `collectors.py:161`, `collectors.py:283`; внешний обработчик — `tools/pf_cli/commands/usage.py:119`.

   Триггер: корректная строка `turn.completed`, затем аналогичная строка с `timestamp: null`, числом, массивом либо объектом.

   Ожидается: явный `malformed_receipt`, сохранение первой записи и cursor на валидном префиксе; CLI возвращает JSON и предусмотренный код ошибки.

   Фактически во всех четырёх случаях возникает необработанный `AttributeError` при вызове `.replace()`. Проверенный префикс не фиксируется: записей `0`, cursor отсутствует. Через `UsageCommand.execute` исключение также выходит наружу, JSON отсутствует.

   Узкое исправление: проверять строковый тип на границе `timestamp()` и выдавать контролируемый `ValueError`, который существующий обработчик преобразует в `malformed_receipt`. Добавить регрессию сохранения префикса и CLI-ответа.

2. **P2 — запись timing metadata создаёт искусственное расхождение часов и завышает occupied time.**

   Место: `tools/codex_exec_worker.py:456`, метод `ManagedUsageCapture.start_execution`; запись с `fsync` находится в `_write_json`, строка `343`.

   Триггер: задержка записи `timing.json`. UTC start снимается перед записью, monotonic start — после неё.

   В детерминированном воспроизведении UTC и monotonic идут одинаково: запись занимает `2 s`, исполнение — `10 s`. Получено:

   | Показатель | Результат |
   | --- | --- |
   | `elapsed_seconds` | `10` |
   | `occupied_seconds` | `12` |
   | `clock_discrepancy_seconds` | `-2` |
   | `clock_quality` | `discrepant` |
   | `execution_quality` | `lower_bound` |
   | Execution внутри шестисекундного окна исполнения | `null` |

   Следовательно, задержка самого учёта превращается в занятость агента и лишает календарные запросы точной длительности даже при согласованных часах.

   Узкое исправление: снимать UTC/monotonic для одинаковых границ измерения без файлового I/O между ними. Предварительную открытую receipt и окончательные наблюдения следует согласовать через существующие revisions.

**Проверки и evidence**

Команда `python -B .pf/artifacts/usage-accounting-review-20261022/review_checks.py` выполнила три исходных набора тестов под Python `3.14.3`: **65 тестов, 0 failures, 0 errors**. Изменено только место временных fixtures в памяти; все создаваемые данные направлены в область артефактов assignment.

В этой области находятся `suite-output.txt`, `reproductions.json`, `clock-pair.json`, воспроизводящий скрипт и `review-log.md`. Оба замечания воспроизведены отдельно после запуска исходных тестов.

Прослежены транзакции revisions/current facts/cursors, replay и конфликты, явный project scope, исключение quarantine, nullable counters, временные агрегации, provider profiles и managed capture. Разделение model/rules/storage/service/provider/CLI соответствует заявленным владельцам; финансовых полей в проверенном публичном API нет.

**READ_ACK**

Прочитаны предоставленные inline inputs, включая domain boundaries, Core placement, amendment независимых часов, review contract, scope/storage decisions и QA handoff. Дополнительно прочитаны релевантные разделы локальных Python-материалов. Проверенные SHA-256:

| Материал | SHA-256 |
| --- | --- |
| `docs.python:root/dataclasses.md` | `9c19c5658aedb68dcf49bf6ccdaa676df31c96f3dea5c9d6fb1e0efe551703c8` |
| `docs.python:root/typing.md` | `cf7a9727d0ef5100fa5b650c9e0ee4f329fdb2f5a11090dae8ca06def9ca4c54` |
| `docs.python-practices:root/pep8.md` | `9c1f6c135bc0a3db8cc1f22a7753a5d970d4cfe8a93da90ddaaf39240689bdb0` |
| `docs.python-practices:root/pep257.md` | `1d300c4bf12d0ada91aff573f6eb45daa933e3fd322cefd7e24a68382b3f3c06` |
| `src/processforge_core/AGENTS.md` | `65abf9c838b8b6c53e9008f8426e9b0b9f3a2c25523281463827ec966f54a988` |
| `.pf/artifacts/pf-framework-architecture-20261005/domain.md` | `c90fe925601522e0f45fb13c282547d7f17e87d958d6c718d7345599557ab649` |
| `docs/concepts/python-core-structure.md` | `64c16acdf70fadc078edcfc4b4bca87ef9c1e6ef26334a250f99ed332569d20a` |

Применены правила явной runtime-валидации — annotations/dataclasses её не обеспечивают; контролируемых исключений; документированных ограничений API; чистых правил без I/O и раздельных владельцев хранения, координации и представления. Фактические разрешённые пути записаны в `read-ack.private.json` как private runtime evidence; публиковать этот файл нельзя.

**Ограничения**

Зарегистрированные Ruff/format/mypy и smoke-проверки учтены по предоставленному primary QA для совпавших байтов, самостоятельно не повторялись. Installed/archive/connected-host acceptance, native Kimi capture и чистота всего репозитория не подтверждаются.

Собственная terminal usage receipt появится после завершения попытки. Её квалификация и проверка unchanged-source replay остаются за primary. Для приёмки необходимы исправление обоих P2 и повтор затронутых проверок.