# Общая проекция метаданных Work: результат

Дата: 2026-10-17 18:11:51 UTC. Результат: PASS_SOURCE_SLICE. Реализация и проверка исходников; установленный Core/Runtime/подключённый MCP не обновлялись.

## Изменение

WorkMetadataReadPass в work/metadata.py получает компактные поля Run/Assignment в исходном порядке и хранит частные наблюдённые факты одной операции. Сводка CurrentWorkService и автоматический каталог WorkRecordCatalogService разделяют проход в pf.context. Штатная фабрика создаёт новый проход при следующей отдельной операции. Источником истины остаётся YAML; process-local YamlParseCache удерживает компактный разбор по текущему содержимому и прежней политике парсера, без увеличения лимитов.

Полные YamlWorkRecordReader.load_run/load_assignment и canonical selection не усекались. Выбранная Work по-прежнему проходит полное актуальное чтение, pins/capsule/scope/access/evidence. Правила OR-активности сводки и AND + pending completion каталога сохранены отдельно. Terminal Run не отбрасываются до проверки журнала. Путь completion-intent поступает от прежнего владельца, а валидатор получает полные актуальные документы. Custom readers и необычные документы без выбранных полей используют прежний полный путь без удержания всей истории проходом.

Обновлены EN/RU document-reads и карта владения Core. Новых CLI/MCP операций, форматов, постоянных индексов, Runtime dependencies, ContextVar-снимка на handler или протокола уведомлений от писателей нет. Изменений флагов raw_hooks/events в этой Work нет.

## Измерения

Полный source tool_result pf.context в отдельных Python-процессах, без server/main. Каждая версия: пять пар cold/warm; cold означает пустой кэш разбора, а не холодный диск или новый процесс перед каждой парой. Обе используют одни project-declared ресурсы установленной поставки и настоящие проверки контекста. Порядок серий: baseline, затем новая версия; одновременно нагружающие CPU проверки не выполнялись. Измерялась основная Work на стадии implementation с action work_incomplete.

| Показатель | До | После |
| --- | ---: | ---: |
| Медиана cold, с | 15.966656 | 6.150534 |
| Медиана warm, с | 16.440742 | 1.624719 |
| Медиана CPU warm, с | 16.218750 | 1.593750 |
| Разборов YAML warm | 2701 | 0 |
| Вытеснений warm | 2701 | 0 |
| Обходов Work на pf.context | 2 | 1 |
| Удерживаемый общий кэш, байт | 67068397 | 41522551 |
| Медиана Working Set warm, байт | 160145408 | 85118976 |
| Peak Working Set процесса, байт | 160985088 | 129806336 |

Ускорение warm: 10.119 раза, снижение времени 90.118%. Cold: 2.596 раза. Итоговая серия after повторена после последней правки пути completion journal; исходная серия использована на том же неизменившемся корпусе. Пробные/предыдущие результаты не смешивались с итоговыми.

Корпус: 1529 файлов Run/Assignment/journal; SHA256 58a9e8ffbf1297fdef207eb3497d6c858f817586d2e18a144b9ccb1c63b15450, одинаков до/после обеих серий. Все 20 полных JSON-ответов равны, SHA256 745405f038985cbec09f5b1f62f554886bbde4e7a1933f5d52a9ccf3535f80fb. Дополнительно полностью совпали 942 строки сводки и 940 записей исторического каталога: SHA256 466c90941109df64ea17a65fb2afa8e5e9e8c799ad6efad4b35f3bd96f069dbc.

Подробности: benchmark-before.json, benchmark-after.json, benchmark-summary.json, records-before.json, records-after.json, parity-and-source.json. Сырые ответы с приватными путями и воспроизводимые helpers/source copies сохранены только в own .pf/tmp; публичные результаты содержат числа/хеши.

## Проверки и контрольные суммы

30 тестов Work record read с 128 сравнением исходных методов и 72 сравнением частичных YAML; 20 Core read tests; 12 YAML cache tests; 8 request-scope tests; 23 Core state tests; 8 Garage/MCP snapshot tests прошли. Selection: 14 сценариев и 53 canonical cases. Native completion recovery прошёл прерывания/повторное завершение и ошибочные journals. Проверены bounded MCP contract, duplicate active Work reuse и 484 scope pairs при native start. Точные результаты/исключения — checks.json.

Сохранены same-size/restored-mtime, read-after-write внутри запроса, удаление/воссоздание, независимость возвращаемых объектов и параллельных проектов, последовательность ошибок, injected falsey ports и full final reads. Дополнительные meaningful cases находятся в прежнем smoke_work_record_read_composition.py. Supporting MCP fixture change доставлена отдельным коммитом 880b8e5af50c9f1fdb1e45aa4d37c8c7d9fa7514; её область не пересекалась с исходниками основной Work.

Полный канонический Git source до изменения проходит native checksum check. Новая полная source copy с собственными изменениями проходит тот же check; 1306 -> 1307 entries, изменены только 12 ожидаемых путей. Новый checksum inventory с LF: a9850bd97b55dc048f2e248961d66a8fa67552cc3200bfd212db9fe718ab44ba. Рабочие source bytes после release-нормализации совпали с измеренной candidate; все изменённые Python-файлы компилируются. Private checkout configuration не включалась в расчёт.

## Границы доказательств

Холодный safe YAML parsing и линейное чтение текущих файлов остаются. Cache bytes — оценка удержания, не лимит RSS. Наблюдённые факты одной операции не являются атомарной транзакцией файловой системы; после write/request нужен новый проход. Потоки с нестандартным injected reader сохраняют полный путь.

Заключительное review выполнено primary после реализации. Независимый агент не запускался; subagent policy запрещает его. Опциональный original-state differential fixture не передавался; directory-symlink qualification недоступна; pyflakes отсутствует и не устанавливался. Прошлая полная release-suite не выдаётся за проверку нового executable source. Archive/installed/Runtime/actual connected-MCP acceptance в этой Work не выполнялась; прежний релизный ZIP не квалифицирует новую реализацию.

Live connected context оставался fresh/Forge. Raw checkout содержит CRLF в package.yaml, Git/installed — LF; copied distribution внутри проекта меняет classifier labels. Для эксперимента выбранные Python-исходники использовали прежний project-declared installed resource root, без подмены результата проверок, refresh snapshot, переписывания installed files или перезапуска. Это source qualification, не доказательство новой скорости уже подключённого MCP.

Публикация исходников и native closeout отражаются в closeout/publication evidence. Следующая отдельная граница — квалификация нового релизного кандидата и, при явном поручении, обновление установленного Core.
