# Review архитектуры

Дата: 2026-10-17 17:13:59 UTC. Роль: primary / architect, самопроверка документа по текущим владельцам кода. Независимое ревью реализации не проводилось: реализации нет.

Результат: pass_with_conditions для предложения архитектуры. Блокирующих противоречий с прочитанными source contracts не выявлено. Условия относятся к будущей реализации и её доказательствам, а не означают уже выполненную квалификацию.

| Сценарий | Решение архитектуры | Основание |
| --- | --- | --- |
| Обе ветки pf.context читают Work | Общий явный read pass; отдельные нынешние policy owners | CurrentWorkService / WorkRecordCatalogService |
| Разные определения active | Не объединять OR сводки с AND + intent каталога | WorkProjectionPolicy / record_catalog.records |
| Завершённый Run с pending intent | Проверять наличие журнала и native validator, не отбрасывать по статусу | CompletionIntentReadService / ValidationService |
| Нет raw run.id, но есть id из пути | Не передавать синтетический id валидатору вместо raw значения | Native intent lookup берёт raw run.id |
| Нет задания / нет tasks / first-assignment | Сохранить разные прежние результаты сводки и каталога | CurrentWorkService.items / catalog.records |
| Одинаковый size/mtime при другой записи | Текущее чтение и content-keyed parse reuse | document-reads / YamlDocumentReader |
| Запись между двумя чтениями в handler | Новый read pass после write; запрет неявного snapshot на весь request_scope | Действующий read-after-write контракт |
| Другая session или проект | Разные снимки; session selection у нынешнего владельца | WorkSelectionService |
| Точная каноническая пара | Сохранить существующий короткий путь и final full live reads | work-selection-canonical plan / selection.py |
| Конкурентная внешняя запись | Наблюдённые метаданные без обещания глобальной атомарности, native final checks | Atomic publisher и отдельные legacy writes |
| Очень длинная история / новый CLI | Честный холодный полный parse, компактное удержание; не обещать O(1) I/O | safe_load_fields / YamlParseCache.load |
| Мало памяти / вытеснение | Существующие bounded budgets, без входного усечения; измерить working set | parse_cache и document-reads |

Условия будущей приёмки: неизменность payload/order/errors, фактическая совместимость injected readers, отсутствие двух глобальных обходов, current-byte проверки, pending-completion матрица, cold/warm wall/CPU/parse/eviction/peak-memory. Точный footprint пока неизвестен. Если тонкий рабочий набор не помещается в нынешний cache budget, отдельно обосновать квоты у существующего cache owner.

При review уточнена формулировка о Core update: пустой RAM-кэш гарантирует новый процесс/загрузка Core; одна замена файлов не обновляет старый запущенный процесс. Сама архитектура не требует перезапуска.

Продуктовые тесты, профилирование нового кода, сборка и установка не запускались. Документ сверён с живым source, required inputs и актуальным PF contract. Следующий шаг — обсуждение/отдельное поручение реализации, без автоматического запуска.
