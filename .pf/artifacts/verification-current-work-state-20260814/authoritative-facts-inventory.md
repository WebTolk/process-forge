# Инвентаризация фактов: verification-authoritative-facts-inventory

## 1) Авторитетные факты (direct evidence)

- Задание `verification-authoritative-facts-inventory` помечено как `planning_only`; `code_changes_allowed: false`, `artifact_changes_allowed: true`.
- Обязательный выход: `.pf/artifacts/verification-current-work-state-20260814/authoritative-facts-inventory.md` (язык `ru`, формат `concise_markdown`).
- Прямые ограничения для агента:
  - `subagent_policy.allow: false`
  - `max_subagents: 0`
  - `allowed_files` только `.pf/artifacts/verification-current-work-state-20260814/authoritative-facts-inventory.md`
  - `allowed_read_files` ограничен списком служебных и runtime/процессных файлов.
- В `project-context.snapshot.yaml` проект классифицирован как `software.python`; `platforms: []`, `selected_knowledge_packages` только web/php docs; `available_tools: []`, `available_mcp: []`.
- Для процесса `knowledge-package-improvement` требуются capabilities `research`, `process_governance`, `review`, `repository_write`; из снапшота удовлетворены только `review` и `repository_write`, `research` и `process_governance` — не доступны (конфликт/недостаток capability).
- `.pf/AGENTS.md` и пакетная структура runtime утверждают файловую модель ProcessForge: доказательства/состояние в `.pf`, этапы через оркестратор/супервизор, без обязательного постоянного daemon-рантайма.
- `tools/pf_runtime/mcp_server.py` и `docs/concepts/runtime-mcp.md`: MCP-сервер read-only, поддерживает `pf.project_state`, `pf.work_state`, `pf.resolve`, `pf.workplace_state`, требует сессионную привязку к ledger.
- `tools/pf_runtime/host.py`:
  - источником projection служит projection `required-output-readiness` из `technical_obligations` процесса и assignment outputs;
  - writes/чтение projection:
    - `.pf/artifacts/projections/stage-obligations.json`
    - `.pf/artifacts/projections/command-history.md`
  - `stage_obligation_rows` возвращает статусы `ready|missing|invalid`;
  - `stage_obligations_payload` учитывает статус `current|stale|missing|invalid` через fingerprint;
  - `rebuild_stage_obligations` и `command_projection_doctor` существуют для диагностики projection.
- `processes/core/process-supervisor.yaml` и `docs/concepts/process-supervisor.md`: supervisor — наблюдательный инспектор, живёт в `.pf/runs`, `.pf/assignments`, `.pf/runtime/agent-runs`, управляет state-доказательствами (`status.json`, `command.json`, `process.json`, `heartbeat.json`, `exit.json`) и в т.ч. tick collect.
- `docs/concepts/runtime-model.md`: модель file-first и event-driven; runtime-цепочка пишет артефакты в `.pf`, события фиксируются в журнале и используются как durable source-of-truth для чтения/восстановления состояния.

## 2) Производные факты (деривативные)

- Задание по своей конфигурации не может изменить кодовую базу и может изменять только один артефакт-отчет.
- Из-за отсутствия capabilities `research`/`process_governance` текущий route формально не закрывает требования upstream-процесса `knowledge-package-improvement` полного цикла (только `review` + `repository_write` доступны).
- Runtime-путь чтения/проверки фактов для этого задания по сути «чтение через обязательные durable артефакты + MCP-запросы» без прямой авторской правки состояния.
- Доступное состояние для проверки — событийный журнал `.pf/runtime/events/events.ndjson` и artifacts/projections; именно через них определяется readiness текущего run.
- Существующая модель делает критически важным разделение:
  - authoritative (статическая спецификация и конфигурация процесса),
  - derived (обновляемые статусы из `host.py` и fingerprint),
  - diagnostic (выводы smoke/тестов и журнальные события).

## 3) Диагностические факты (runtime/runtime-read path)

- `.pf/contexts/project-context.snapshot.yaml` в состоянии `fresh` на момент формирования задачи; содержит конфликтные capability как фактический сигнал неполной конфигурации.
- `.pf/artifacts/projections/stage-obligations.json` для текущего run: payload с source authority и пустым `obligations` в считанном сегменте.
- `tools/smoke_stage_projectors.py`:
  - подтверждает поведение `rebuild-projections` / `projection-doctor`;
  - подтверждает логику stale/missing и работу `command-history.md`.
- `tools/smoke_runtime_host_poc.py`:
  - подтверждает изоляцию routing событий по `project_root`;
  - подтверждает обработку duplicate events и supervisor/collector потоки.
- `tools/smoke_runtime_ledger_hooks_mcp.py`:
  - подтверждает, что MCP-сессия и project binding обязательны;
  - cross-project event usage/неверный `project_root` блокируются.
- `tools/smoke_worker_*`:
  - подтверждают формат durable worker state (`command.json`, `status`, `exit`, heartbeat);
  - подтверждают присутствие `workspace_access` в командном контексте и проверку путей.

## 4) Недостаточные факты (для валидации осталось проверить)

- В рамках доступного среза не была подтверждена полная выгрузка всех диагностических артефактов последнего `stage-projectors-next` прогона (нужен просмотр полного артефакт-лога при дальнейшей сверке).
- Файл `задания/process-forge-verification-current-work-state-detailed-master-prompt.md` прочитан, но для полного точного перечня задачной риторики требуется дополнительный clean-read (в некоторых местах вывод неструктурный из-за локальной кодировки/отображения).
- Не показан итоговый сравнительный снимок всех readiness-полей всей сессии в одном месте; сейчас есть фрагменты evidence и последняя NDJSON-лента с событиями `assignment.started`.

## 5) Вердикт для текущего run

- Проверочная картина верифицируема: для этого run фактически есть достаточный авторитетный и диагностический каркас для инвентаризации.
- Главный пробел — capability-путь (`research`/`process_governance`) и отсутствие некоторых полноценных диагностических слоёв в одном артефактном срезе.
- Рекомендация: считать задачу в пределах цели инвентаризации выполненной с маркером “доказательная база достаточна для отчёта, но не для полного процесс-диагноза capability-complete”.