# ProcessForge 1.2.0: dev-релиз, установка и предрелизная проверка

Дата: 2026-10-17. Dev-кандидат установлен, PF app-server перезапущен и принят. Полный финальный consumer suite, 13 проверок установленного CLI, HTTP, SQLite и независимого установленного MCP прошли. **Последний открытый гейт — новый код в фактически подключённом MCP хоста:** его прежний процесс продолжает работать. Work сохранена на release-delivery для точного продолжения; готовность публичного stable-релиза не заявляется.

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
| Фактически подключённый MCP | Context fresh/Forge, exact Work/resource PASS, текущая переписка читается; **новый код не загружен**, процесс прежний |

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

Серии CLI/MCP выполнены последовательно после функциональных проверок, с обычными фоновыми scheduler/hooks. Ответы нового MCP во всех шести вызовах context совпали. Новый независимый stdio и фактический host — разные слои доказательства; эта таблица не выдаётся за контролируемый A/B. Контролируемая source серия из предыдущей Work дала 16.441 -> 1.625 с на неизменном корпусе и 20 одинаковых полных ответах.

Сервер: три пригодных 30-секундных окна, всего90.029 с, CPU15.828 с = **4.395% всей мощности четырёх логических CPU** (17.581% одного ядра). Working Set171.961–171.988 MiB, peak176.715 MiB; тот же процесс, до/после ready/scheduler_alive/workers0/jobs0. Исходное третье окно зацепило контрольную PF-команду; оно исключено до чтения результата и заменено отдельным чистым окном. Все исходные и замещающие данные сохранены. Замеры относятся этому устройству и текущей нагрузке.

## Открытая приёмка и ограничения

1. **Переподключить существующий PF MCP в хосте.** Оба процесса существующего соединения имеют прежние PID и запуск до apply; после замеров отдельный новый stdio корректно завершён. На диске установлен8ea152b, но существующий host ещё исполняет предыдущую реализацию. Доступные native PF команды управляют регистрацией MCP; операции переподключения текущего host transport в доступной поверхности нет.
2. После переподключения проверить новый process/start/root относительно применённого manifest, actual fresh pf.context, exact Work valid/ready и один authorized resource resolve; затем один warm-up и пять коротких замеров actual pf.context. **Apply и перезапуск app-server повторять не нужно.** Exact native continuation и checkpoint описаны в governed handoff.
3. Bounded shutdown observer на большой истории способен отказать в guarded stop; текущий операторский override выполнен после полной положительной проверки. Это эксплуатационное ограничение сохранено, product defaults не менялись.
4. Metrics sessions/work/workers по бюджету остаются partial; unknown не заменены нулём. Исторические invalid/unreadable presence records не исправлялись. Реальные Linux/macOS и матрица Python, optional directory-symlink/original-state fixture, новый реальный Codex worker после этой установки не квалифицировались. Полные изолированные worker/driver scenarios и актуальная driver validation прошли.

Primary review — source-review.md, без независимого агента: subagent policy запрещает его. Native Work остаётся release-delivery до фактической приёмки нового MCP. Публикация source подтверждена source-publication-final.json; доставка отчёта/checkpoint фиксируется отдельным scoped commit и полным readback двух dev-веток. Старую terminal Work проекции/фикстуры не возобновлять.
