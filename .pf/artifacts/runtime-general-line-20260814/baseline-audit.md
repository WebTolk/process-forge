# Базовый аудит: PF Runtime в генеральной линии

- date: `2026-08-14`
- run: `runtime-general-line-20260814`
- source: `задания/process-forge-runtime-general-line-master-prompt.md`
- scope: аудит перед первым implementation slice; продуктовый код на этом этапе не менялся.

## Вывод

PF Runtime должен остаться workplace-scoped transport/host слоем над PF Core. Его
нельзя превращать в отдельный Ledger, Director, Inspector, event store или process
engine. Первый срез должен исправить подтвержденные defects Runtime, не меняя
семантику Core.

## Runtime и Ledger: классификация текущего состояния

| Данные | Текущее место | Классификация | Решение |
| --- | --- | --- | --- |
| identity, presence, heartbeat, lease, process/run refs | существующий Agent Ledger | authoritative | Runtime только вызывает существующие Core maintenance/read paths. |
| normalized event journal | `.pf/runtime/events/events.ndjson` через PF Core | authoritative facts | Принимать через существующий `append_process_event`; не создавать второй store. |
| process/worker state | `.pf/runtime/agent-runs/**`, Inspector/Supervisor | authoritative | Runtime наблюдает через Core и восстанавливает status после restart. |
| `service.json`, lock, endpoint, token reference, scheduler timestamps | `<workplace>/runtime/pf-runtime/` | transport-only | Оставить как lifecycle/IPC state Runtime. |
| `state.json.projects` project handles | `<workplace>/runtime/pf-runtime/` | derived cache | Допустим только как rebuildable cache Project Router, не как источник project truth. |
| `state.json.sessions` session-to-project mapping | тот же runtime state | duplicate/cache | Сократить в следующем Ledger-centric slice: binding должен проверяться через Ledger; persisted Runtime mapping только миграционный/rebuildable cache. |
| generated `command-history`, changed-files и status views | projections/artifacts | derived | Проекторы принадлежат Core, Runtime лишь запускает их. |

## Подтвержденные defects и blockers

1. `/event` принимает `project_root` из payload без общей проверки session-to-project binding. Read endpoints проверяют scope, event ingestion — нет.
2. Runtime обслуживает IPC через `ThreadingHTTPServer`, но JSON atomic-write использует временное имя только с PID. Одновременные request/scheduler записи могут столкнуться.
3. `active_service()` считает service active при живом PID даже когда `/readyz` не отвечает. Это мешает stale recovery при hung process или PID reuse.
4. `smoke_long_lived_runtime.py` нестабилен на Windows: oversized request дал `WinError 10053`, потому что server отклоняет body до его чтения, пока client продолжает передачу.
5. `project-context-check` блокируется stale classification и отсутствующими required capabilities `markdown_editing`, `repository_read`, `schema_validation`. Из-за этого `worker-run` не смог подготовить capsule для независимого shell-worker review.
6. checksum inventory stale; release gate пока не может быть закрыт.

## Codex hooks

Текущая Runtime ingress принимает normalized adapter events. Подтвержденного активного
lifecycle-hook binding в текущей Codex session нет: manual adapter ingress работает,
а автоматическое self-observation не доказано. Поэтому live Codex adapter является
отдельным последующим slice и не должен навязывать Runtime собственную session model.

## Первый implementation slice

Владелец: один writer для `tools/pf_runtime/**`, runtime CLI wiring и двух Runtime
smokes. В срез входят:

1. единая проверка session-bound project identity, включая `/event`;
2. сериализация/уникальные temporary paths для Runtime state writes;
3. корректная liveness-проверка и stale/PID-reuse recovery;
4. детерминированный Windows oversized-IPC contract;
5. regression tests: cross-project event denied, concurrent state writes, unresponsive-live PID recovery, predictable oversized request failure, crash/restart and no project mix-up.

В срез не входят: новый Ledger, новый event store, remote sync, Web UI, LLM routing,
автозапуск как Windows Service и broad context-registry repair.
