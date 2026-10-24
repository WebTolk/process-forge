**W1 R02 — владение данными и первый срез хранения**

Дата: 2026-10-24. Статус анализа: `ready_for_review`. Реализация и функциональная приёмка не выполнялись.

Identity: `pf-r02-design-20261024` / `pf-r02-w1-domain-design-20261024` / `pf-r02-w1-domain-design-20261024-capsule`, попытка 2. SHA-256 capsule совпал с prepared input. Новая Work, пересборка контекста и переходы lifecycle не выполнялись.

**Рекомендуемый первый срез**

Перенести состояние попыток исполнителей и выборку текущих физических исполнений в основную проектную SQLite-базу. Перевести существующих читателей и писателей на один репозиторий. Канонические YAML задач и запусков, immutable capsules и содержательные артефакты пока сохраняют своих владельцев.

Это устраняет зависимость stop/busy guard от накопленной истории, не требует одновременного переноса всех доменов и оставляет дальнейшую консолидацию последовательной.

**Фактические владельцы**

| Данные | Текущий владелец и точки доступа | Граница первого среза |
| --- | --- | --- |
| Идентичность и конфигурация проекта | `ProjectMetadataReader`, `ConfigService`, `YamlConfigStore`; проектные YAML | Сохраняются вне настраиваемой SQL-базы |
| Run, assignment, stage и completion | `ProcessExecutionService`, `WorkStartPublicationService`, `WorkTransitionCommitService`, `CompletionIntentReplayService`; чтение через `YamlWorkRecordReader` | Проект остаётся владельцем; workplace получает проекции |
| Capsules и закреплённые входы | Проектные immutable файлы; `WorkerAssignmentService`, `WorkerCommandBuilder` | Сохраняются байты, checksum и точные selectors |
| Содержательные артефакты | Объявленные файлы проекта; `WorkOutputPolicy` проверяет пути, наличие и fingerprints | SQL хранит ссылки и проверочные факты, не конкурирующую редактируемую копию |
| Попытки исполнителей | `write_agent_run_state`, `load_agent_run_state`, `observe_worker_run`, worker-run команды в `tools/processforge.py` | Основной кандидат переноса в проектный SQL |
| Process/heartbeat/exit evidence | Controller, `tools/codex_exec_worker.py`, `tools/prepared_executor.py` | Producers сохраняют receipts; один lifecycle service интерпретирует их |
| Сессии, присутствие и leases | Workplace Agent Ledger; `AgentWorkplaceRegistry`, `AgentPresenceReader`, команды checkin/heartbeat/lease | Пока без переноса; присутствие агента не доказывает активность worker-процесса |
| Chat и telemetry | Проектные `ChatTranscriptWriter`, `ChatTranscriptReader`, `TelemetryEventService` | Пока без переноса; события ссылаются на сообщения |
| Приём событий, pending dispatch, verification | Проектные `ProcessEventJournal` и `RawHookJournal` | Обязательные operational facts сохраняются независимо от настройки истории |
| Accounting | `WorkplaceAccounting`, `SQLiteAccountingRepository` | Существующие данные сохраняются; дополнительная постоянная worker-база workplace не создаётся |
| Workplace summaries и поиск | Host/metrics — проекции; `ResourceIndexBackend` — отдельная граница производного поиска | Сводка не становится владельцем проекта; поисковая база остаётся отдельной |

Точные файлы, символы, идентификаторы и предлагаемые изменения перечислены в `implementation-map.json`.

**Подтверждённые проблемы текущего пути**

- `runtime/metrics.py::shutdown_workers` вызывает `observe("workers", ...)`, который обходит `.pf/runtime/agent-runs/*/*/status.json`. Исчерпание бюджета делает счётчик неизвестным.
- `RuntimeProcess.active_worker_count` в `tools/pf_runtime/service.py` отдельно сканирует тот же исторический каталог.
- `command_worker_run_start` вызывает `Popen` перед публикацией `running` и `process.json`. Для безопасной остановки необходима durable reservation до создания процесса.
- `WorkerObservationInputService.process_pid_running` проверяет существование PID; этого недостаточно для защиты от повторного использования PID.
- Существующие SQLite-владельцы проверяют database-wide `application_id` и `user_version`. Простое перенаправление всех репозиториев в общий файл несовместимо с их текущими контрактами.

**Предлагаемый доменный контракт**

Идентичность попытки: `(project_id, run_id, assignment_id, attempt)`. Дополнительный внутренний `execution_instance_id` различает поколения физического исполнения. Абсолютный путь используется для маршрутизации, PID — для наблюдения; они не заменяют устойчивую идентичность.

Отдельно учитываются lifecycle процесса, наблюдение его идентичности, готовность collection, ревизия и readiness миграции. Завершение процесса не означает принятие результатов задачи. Неполный collection сам по себе не означает работающий процесс.

Проектный репозиторий содержит историю попыток и индекс незавершённых физических исполнений. Терминальная запись и исключение из текущего набора фиксируются одной транзакцией. Обычные start/status/stop читают текущий набор; история выдаётся индексированными страницами со стабильным курсором.

Heartbeat/exit receipts применяются идемпотентно к точной попытке. Поздний receipt старой попытки не может изменить новую. После переключения `status.json` становится совместимым представлением; обратный импорт ручных изменений запрещён.

Неопределённость текущего исполнения препятствует idle. Неполнота необязательной завершённой истории не создаёт busy. Удаление или устаревание workplace-проекции никогда не превращается в доказанный ноль.

**Переход и совместимость**

1. W2/W4 фиксируют расположение основных БД, единую физическую identity и версии схем по доменам. Новая постоянная `workers.sqlite3` не предлагается.
2. Явная миграция импортирует доступные legacy records с provenance, checkpoint, проверкой конфликтов и readiness-барьером. Отсутствующие исторические попытки не реконструируются догадками.
3. Все worker writers/readers переключаются согласованно. Старые файлы сохраняются; dual-write с двумя независимыми владельцами запрещён.
4. W3 заменяет оба исторических обхода и согласует общий admission fence для CLI и Runtime. Один `RuntimeProcess.state_lock` гонку между процессами не закрывает.
5. После приёмки worker-среза последовательно консолидируются проектные events/hooks, затем workplace Ledger/presence/leases. Перенос canonical task/run storage требует отдельного переключения всех lifecycle/recovery consumers.

CLI/MCP сохраняют параметры, payloads, ошибки и пути отчётов. File-only работает через локальный Core/SQLite без обязательных daemon, MCP, сервера БД или LLM. Чтение отсутствующей БД не должно создавать её.

При переносе проекта сохраняются IDs, относительные пути артефактов и проектная БД. Workplace mappings восстанавливаются явно; конфликт одинаковых project IDs требует проверки.

Generated Markdown может перестраиваться только из объявленного canonical source с ревизией и свежестью. Содержательные отчёты и approved evidence не становятся автоматически перезаписываемыми проекциями.

**Implementation map**

Артефакт: `.pf/artifacts/pf-r02-storage-foundation-20261024/w1-domain/implementation-map.json`, `schema_version: 1`.

Предлагаемое непересекающееся владение:

| Участник | Ответственность |
| --- | --- |
| W1 | Новые `executions/model.py`, `executions/ports.py` и документ доменного контракта |
| W2 | Новый общий `storage/*`, SQLite driver, schema/composition; необходимые изменения configuration/accounting |
| W3 | Execution repository/service, worker lifecycle и все общие integration files, включая `tools/processforge.py`, Core composition, metrics, Runtime и wrappers |
| W4 | Execution migration и существующие maintenance/backup/update/transfer owners |

Полные списки файлов находятся в карте. Изменения CLI-регистрации от W2/W4 передаются W3 последовательно. Карта является предложением для следующих scoped Work и не выдаёт права реализации.

**Проверки и ограничения**

JSON карты успешно разобран; identity совпала; пересечений предложенных областей записи — 0; конфликтов новых путей с существующими файлами — 0. SHA-256 15 опорных исходников повторно совпали. Абсолютных путей в карте нет. Проверка завершилась с exit code 0.

Анализ статический. Продукт и тесты не изменялись; pytest, Ruff, mypy и benchmarks не запускались. Для artifact-only вклада эти проверки неприменимы. Совместимость выполнения пока не доказана.

Для реализации обязательны: 400 000 завершённых попыток при 0/1/нескольких текущих исполнениях; планы запросов и число чтений; start/stop race; crash/restart; PID reuse; stale heartbeat; старые receipts после retry; migration resume/rollback; прежние CLI/MCP/file-only сценарии. Кандидаты существующих smoke-проверок перечислены в карте.

Serena/IDE отсутствовали; использован ограниченный shell fallback. Некоторые временные тестовые каталоги недоступны; обход ограничений не предпринимался. Живые БД и накопленная runtime history не открывались.

**Блокер native coordination:** prepared scope разрешает только `read` и `write_artifact` в области W1 и не выдаёт прав на мутации Ledger/chat. Поэтому READ_ACK, heartbeat и RESULT_READY не отправлены; выполнение этого обязательства не подтверждено. Если оно необходимо для приёмки вклада, требуется новая подготовленная выдача с явным разрешением этих действий для собственной identity исполнителя. Существующая capsule не изменялась.