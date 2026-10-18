# Системная проверка и замеры PF1.2.0
Дата: 2026-10-17T14:23:02.178923+00:00

Результат: установленный dev-кандидат, живой Runtime и фактически подключённый MCP проверены. Осталась конкретная документационная правка перед новым финальным архивом. Стабильная публичная публикация этой проверкой не выполняется.

## Идентичность и достаточность существующих проверок
- Проверенный source commit: d5947ea6ab4a186dc4d9958aa19010a6dfc5c711; tree21d293db28124fc0f82459678d1c28b9add0e1b1.
- Retained dev ZIP SHA256:8103664d38b48543a91c1d3b1ed0760c3135732abaf2e4e34b3bc40b7d900045, 1308entries. Sidecar, все archive member hashes, Core manifest и installed manifest согласованы.
- Установка:1.2.0, incomplete_update=false; 1306owned-файлов сверены. Отдельная локальная .pf/process-forge.yaml совпадает с прежним предобразом.
- После квалифицированного source нет committed release-file changes. Working tree отличается от ZIP только сохранённой проектной конфигурацией после учёта CRLF/LF; 261текстовых файлов имеют исключительно представление переводов строк.
- Полный штатный source release-test274/274 PASS за2431.945с, исходный public=false; individual statuses и exit codes перепроверены. Повторного полного запуска не было. Native archive quick, extracted7 и installed5 PASS подтверждены квитанциями на этот hash; пересекающиеся сценарии не суммируются.
- Actual MCP запущен после latest native update, из installed Core; snapshot fresh, exact Work valid/ready, positive Python resolve complete и negative resource_not_in_work подтверждены. Исходники, ZIP, installed, Runtime и connected MCP остаются отдельными слоями доказательств.

## Скорость команд
Для каждой операции:1прогрев,5измерений; median и полный min–max, wall clock. CLI включает создание нового Python-процесса; MCP включает transport. Поэтому разные поверхности не объявляются прямым A/B сравнением. Все вызовы успешны.

| Поверхность | Операция | Median, с | Min–max, с |
| --- | --- | ---: | ---: |
| CLI, отдельный процесс | version | 0.753 | 0.726–0.817 |
| CLI, отдельный процесс | project-context-check | 1.571 | 1.540–1.664 |
| CLI, отдельный процесс | work-state | 0.882 | 0.821–0.895 |
| CLI, отдельный процесс | work-resolve | 1.837 | 1.834–2.041 |
| MCP, подключённый процесс | pf.context | 14.675 | 14.637–14.836 |
| MCP, подключённый процесс | pf.work.state | 0.053 | 0.039–0.061 |
| MCP, подключённый процесс | pf.work.resolve | 2.087 | 1.743–3.320 |
| MCP, подключённый процесс | pf.work.search | 2.102 | 1.990–2.144 |

Реальный work-start текущей Work занял12.0с на поверхности tool. Лишние Work ради статистики не создавались. Прежние16октября одиночные CLI observations2.730/2.505/5.214с имеют другую нагрузку; из них не выводится точный процент ускорения. pf.context14.675с остаётся отдельным P2 performance follow-up с необходимостью профилировать полный context path.

## CPU и память
Три30с окна по одному OS handle на каждый процесс; PID/start identity не менялась. Во время окон foreground PF-команды и workers отсутствовали; обычные scheduler/hooks продолжали работать. Нормальные file/tool обращения снаружи процесса не останавливались.

| Окно | Wall, с | CPU одного ядра | CPU всего устройства4CPU | Working set в конце | Private bytes в конце |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 30.000 | 33.958% | 8.489% | 151.58 MiB | 169.16 MiB |
| 2 | 30.000 | 26.875% | 6.719% | 150.46 MiB | 168.04 MiB |
| 3 | 30.001 | 26.041% | 6.510% | 150.31 MiB | 168.04 MiB |

За90.001с Runtime израсходовал26.0625CPU-с: 7.239% всей мощности4CPU, 28.958% одного ядра. Actual MCP в трёх окнах израсходовал0.0CPU-с на разрешении счётчика ОС; это не обещание строго нулевой фоновой работы. Его working set около143MiB. Runtime ready до/после, active_workers=0, scheduler_alive=true.
Прежний60с замер того же dev Runtime был4.5963%; нынешние6.51–8.49% показывают зависимость от нагрузки/окна. Исторические79.7% одного ядра16октября не являются сопоставимым controlled baseline. Новая причина либо улучшение алгоритма в этой Work не заявляются.

## Матрица покрытия
| Подсистема | Сценарий | Результат/слой | Доказательство | Пробел или граница |
| --- | --- | --- | --- | --- |
| Установка/updater | Повторная сверка архива, manifest и установленного payload; настройки сохранены | PASS, live + reuse | identity.json; core-update-status.json; historical native apply | Apply/recovery заново на устройстве не выполнялись; изолированные updater-сценарии входят в274. |
| CLI | Новые процессы version/context-check/exact Work/resource | PASS, 24 вызова | cli-latency.json | Одна версия CPython на Windows, обычная текущая нагрузка. |
| MCP | Свежий context, exact Work/search/resolve и отказ неразрешённому ресурсу | PASS, live | mcp-latency.json; resource-denial.json | pf.context медленный:14.675с median; транспорт включён во время. |
| Контекст/знания/доступ | Fresh snapshot; immutable context valid; Python fulltext complete; search doctor | PASS, live | mcp-latency.json; capsule-doctor.json; search-index-doctor.json | Project-artifacts/profile имеют metadata navigation; derived reports могут быть stale без stale context. |
| Work/lifecycle/continuation | Exact restart continuation, завершение предшественника, новый bounded start и evidence transitions | PASS, live | predecessor stage evidence; текущие stages; native terminal/readback | Admission один реальный запуск12.0с tool wall, статистики admission нет. |
| Процессы/catalog/pins | Сохранён process1.2.0 fingerprint; catalog/process/selection controls | PASS, reused274 | full-source-suite/latest-report.json; current capsule | Новых process/schema versions и migrations capsulе нет. |
| Workers/collect/recovery | Worker/supervisor/collect controls; реальный native worker16октября | PASS, reuse с границей | full274; archive7; prior worker report/closeout | Живой новый worker после последнего dev update не запускался; не заявляется новая полная end-to-end приёмка каждого сценария. |
| Ledger/leases/chat | Live native doctors; chat/conversation replay и integration controls | PASS, live + reuse | agent-ledger-doctor.json; agent-lease-doctor.json; archive7/installed5 | Исторические task outcomes и failed attempts сохраняются; новые сообщения другим агентам не отправлялись. |
| Scheduler/director/inspector/metrics | Actual ready/scheduler_alive до и после90с; исходные failed/recovery видимы | PASS с ограничениями | runtime-before/after-quiet.json; runtime-doctor.json | Metrics sessions/work/workers partial: budget; sessions также invalid/unreadable. Не заменены нулями. |
| Diagnostics/egress/границы | Native diagnostics status, core admission/diagnostics/egress suite | PASS, live + reuse | diagnostics-status.json; full274 | Профили конфигурации, budgets и security authority не менялись. |
| SQLite/накопленная история | Две действующие project-local базы quick_check=ok; journals/replay controls | PASS, live + reuse | live-diagnostics.json; full274 | Legacy import/cutover не повторяется; SQLite WAL требует local storage/backup API. |
| Документация/упаковка | Проверены EN/RU notes, migration и CHANGELOG относительно последних изменений | Найдена необходимая правка | documentation-followup.md | YAML-cache отрицание и пропущенные последние изменения; final docs/archive оформляются следующей scoped Work. |
| Переносимость | Фактический Windows/CPython run, прежние доступные interpreter controls | Ограничено | cli-latency.json; old release qualification | Linux/macOS и полная матрица Python здесь не проверялись. |

## Review и следующие действия
Проверку плана, результатов и ограничений выполнил primary; subagent_policy.allow=false. Отдельного независимого ревью именно этого отчёта не было. Existing source/archive reviews и274/274 не подменяют новые native receipts.
Все7native diagnostic commands после исправления двух ошибочных экспериментальных --json invocations завершились exit0; ошибочные receipts сохранены как usage errors, не как продуктовые отказы. Обе SQLite quick_check=ok.
Ограничения: медленный context, частичные metrics, отсутствие новой actual worker attempt и Linux/macOS. Данных о новой продуктовой регрессии в выполненных сценариях нет. Готовность стабильной публикации требует согласованных notes и точного final archive.
Конкретная правка пяти release/migration/CHANGELOG документов плюс checksum inventory подготовлена в documentation-followup.md. Её выполняет следующая отдельная bounded Work; настройки, история, установленный Core и сервисы не меняются. Legacy backlog pf120-installed-systems-check-20261016 будет закрыт ссылкой на эти результаты при доставке его ожидаемого отчёта.
Измерительные скрипты retained как локальное воспроизводимое evidence под собственным .pf/tmp; raw device receipts не включаются в public summary.
