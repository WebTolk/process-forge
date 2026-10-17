# ProcessForge 1.2.0: dev-релиз, установка и предрелизная проверка

Дата: 2026-10-18 (местное время). **Предрелизная приёмка установленного dev-кандидата 1.2.0 / 8ea152b завершена по всем согласованным слоям.** Полный финальный consumer suite, 13 проверок установленного CLI, HTTP, SQLite и независимого установленного MCP прошли ранее; фактически подключённый MCP принят после переподключения. Проверены новый процесс после apply, установленный код, fresh context, точная Work, разрешённый ресурс и поиск. Stable tag, update feed и публичные release assets требуют отдельной поставки.

Итог фактического подключения: [actual-host-acceptance-20261018.json](actual-host-acceptance-20261018.json). Исторические checkpoint и receipts от 17 октября сохранены; их прежняя отметка pending относится к состоянию до переподключения.

## Точная поставка

- Source: **8ea152bfa6376a66fc87c7ed48d74eacc5c2ad41**, tree **16f63bae232fd161a5f721428bb1cc1096bf6d7d**. Обе dev-ветки прочитаны с полным SHA. Проекция доставлена отдельным 280e00d, поправка существующего constructor smoke — отдельным 8ea152b.
- [Dev ZIP](../../tmp/pf120-dev-release-20261017/processforge-1.2.0-dev-20261017-metadata-r2.zip): 2538277 байт, 1309 записей, SHA256 **e332a74de958b2daad9711644bd848a82d1024b83bd03c47537377a27884a7dc**.
- [Sidecar](../../tmp/pf120-dev-release-20261017/processforge-1.2.0-dev-20261017-metadata-r2.manifest.json): SHA256 **d9fc5b9fcc670d5d59b141aa26c6fa5dec287233153a6f23062b72cc6c0b9233**.
- Native release-pack выполнен из чистого detached LF worktree. Версия Core — 1.2.0, dev-кандидат определяется commit/hash. Stable tag/update feed и публичные release assets не публиковались.

## Покрытие и результаты

| Слой / функции | Результат |
| --- | --- |
| Полный public source suite первого candidate | 274 checks: 273 PASS, 1 устаревший constructor expectation; 1605.294 с. Исходный FAIL сохранён |
| Исправление обнаруженной проверки | Точный список прежних параметров сохранён, добавлены optional work_metadata / KEYWORD_ONLY / None; все 7 существующих тестов PASS |
| Продуктовые байты после поправки | Между ZIP отличаются только test, inventory и generated Core manifest; весь production payload одинаков |
| Финальный native release-archive-test full | PASS, 1481.688 с; внутренний полный public suite 1474.78 с. Проверены архив/manifest/source hashes и обе CLI entrypoints |
| Work, процессы, scopes/capsules/evidence/continuation/recovery | Полный source и финальный consumer охватывают эти семейства; точная установленная Work valid/ready |
| CLI/MCP framing, Unicode, malformed input, actions/contracts | Полный source/consumer; installed CLI/help и новый stdio handshake/tools list прошли |
| Context/resources/search/YAML/пакеты/авторинг/updates | Полный source/consumer; installed context-check, resource, search doctor и driver validation PASS |
| Runtime/config/Monitor/sessions/Ledger/workers/hooks/chat/journals | Полный source/consumer; installed Runtime/Monitor, workplace/Ledger/lease/capsule doctors PASS |
| Установленные файлы | Manifest точно равен ZIP; 1307 payload files совпали, существующая локальная .pf/process-forge.yaml сохранена с прежним SHA |
| Реальные SQLite hooks/events/search | Три read-only PRAGMA quick_check: ok |
| HTTP работающего сервера | readyz200/ready; status без токена и с неверным токеном401, с правильным200; проверен тот же instance |
| Новый независимый installed MCP | PASS: 31 tools, fresh/Forge, exact Work valid/ready, docs.python resolve available, поиск ready/5 matches |
| Фактически подключённый MCP | **PASS после переподключения:** новая пара процессов принадлежит Codex и запущена после apply; installed manifest/metadata совпадают с checkpoint; fresh context, exact Work valid/ready, docs.python:root и поиск ready |

Подробная матрица всех source checks: source-full-results.json. Единственный source failure закрыт узкой test-only поправкой и полным финальным consumer suite. Единый полный повтор последнего source tree не заявляется. Consumer запущен без custom --only/--skip, native timeout_scale=2: внешний лимит 2400 с выбран после наблюдавшихся 1605 с source suite. Полные логи и исходные native traces сохранены локально; безопасные receipts содержат exit code/hash, а не машинные команды.

## Установка и перезапуск

Свежие context/Work перед установкой — fresh/Forge и valid/ready. Native plan: added1, changed19, removed0, no blockers. Новый ZIP применён **ровно один раз** штатным core-update apply --confirm. Status: 1.2.0/source8ea152b/1308 managed files/incomplete_update=false, native backup сохранён. Прежний успешный update и первый ZIP999667c5 не повторялись.

Два guarded stop отклонены из-за неполного bounded worker observer. Полная read-only проверка тем же native observer охватила оба проекта, running0/complete/issues[]; прочитаны 2280 entries/169 files за 0.324 с. Default пределы512 entries/128 files давали partial/budget. После этого запрошенный операторский перезапуск выполнен штатным мягким server stop --force, затем single apply и server start с прежними interval10.0/port0. Решение и точные receipts — operational-decision-02.md, quiescence.json, apply-summary.json.

Новый процесс/instance подтверждён, ready/scheduler_alive. Все пять защищённых файлов сохранились побайтно: конфигурация устройства, workplace manifest, обе локальные project-конфигурации и project context snapshot. **raw_hooks=false, events=true**, revision прежний. История не переносилась и не очищалась. Переписка доступна через действующий session chat.

## Скорость и ресурсы

| Поверхность / операция | Медиана | Диапазон, с |
| --- | ---: | ---: |
| Новый installed MCP stdio: pf.context, 5 после warm-up | 1.849 с | 1.594–1.919 |
| Новый installed MCP: exact Work, один вызов | 0.018 с | — |
| Новый installed MCP: resource / search, по одному вызову | 0.887 / 1.047 с | — |
| Installed CLI: version, 5 новых процессов | 0.774 с | 0.731–0.889 |
| Installed CLI: exact Work, 5 новых процессов | 0.832 с | 0.816–0.861 |
| Installed CLI: resource, 5 новых процессов | 1.966 с | 1.908–2.218 |
| Installed CLI: context-check, 5 новых процессов | 1.654 с | 1.602–1.906 |
| Существующий MCP хоста: pf.context, один вызов | 14.254 с | прежний процесс |
| Фактически подключённый MCP после переподключения: pf.context, 5 после warm-up | **2.021 с** | **1.950–2.403** |

Серии CLI/MCP выполнены последовательно, с обычными фоновыми scheduler/hooks. Ответы независимого MCP во всех шести вызовах context совпали. После переподключения выполнена отдельная последовательная серия на фактическом соединении: warm-up 4.779 с и пять замеров 1.950/2.014/2.292/2.403/2.021 с; все шесть полных ответов совпали. Здесь измерено время вызова инструмента целиком. Новый независимый stdio и фактический host — разные слои доказательства; эта таблица не выдаётся за контролируемый A/B. Контролируемая source серия из предыдущей Work дала 16.441 -> 1.625 с на неизменном корпусе и 20 одинаковых полных ответах.

Сервер: три пригодных 30-секундных окна, всего90.029 с, CPU15.828 с = **4.395% всей мощности четырёх логических CPU** (17.581% одного ядра). Working Set171.961–171.988 MiB, peak176.715 MiB; тот же процесс, до/после ready/scheduler_alive/workers0/jobs0. Исходное третье окно зацепило контрольную PF-команду; оно исключено до чтения результата и заменено отдельным чистым окном. Все исходные и замещающие данные сохранены. Замеры относятся этому устройству и текущей нагрузке.

## Приёмка фактического подключения и ограничения

Новая единственная пара PF MCP запущена после завершённого apply, launcher принадлежит Codex; путь установленного MCP и workplace совпадают с сохранённой поставкой. Manifest и work/metadata.py имеют прежние SHA256. Все 1307 payload files совпали с финальным ZIP; единственная локальная project configuration и все пять защищённых файлов сохранены. Исторические pins отчёта/handoff проверены до их обновления. Вызовы выполнялись через фактически подключённый инструмент; дополнительный stdio для этой приёмки не запускался.

Context fresh, snapshot прежний; exact native continuation resumed, Work valid/ready на release-delivery, docs.python:root available, поиск ready. Runtime ready/scheduler_alive, тот же владелец/instance после установки, workers0/jobs0. raw_hooks=false/events=true и configuration revision прежние. Apply, server restart и refresh контекста не повторялись.

Сохранены эксплуатационные ограничения: bounded shutdown observer на большой истории может отказать в guarded stop; прежний операторский override выполнен после полной положительной проверки. Metrics sessions/work/workers по бюджету остаются partial; unknown не заменены нулём. Исторические invalid/unreadable presence records не исправлялись. Реальные Linux/macOS и матрица Python, optional directory-symlink/original-state fixture, новый реальный Codex worker после этой установки не квалифицировались. Полные изолированные worker/driver scenarios и актуальная driver validation прошли.

Primary review — source-review.md и acceptance-review-20261018.md, без независимого агента: subagent policy запрещает его. Native release/evolve closeout, doctors и доставка evidence отражаются в closeout-20261018.json и delivery-publication-20261018.json. Публикация source подтверждена source-publication-final.json. Исторический resume-checkpoint.json сохранён; после terminal closeout эта continuation не предназначена для повторного запуска. Готовность dev-кандидата на этом устройстве не публикует stable-релиз автоматически.
