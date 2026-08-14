# WARN

## 1) Условие гонки при параллельном `runtime start` на одном workplace

**Severity:** MEDIUM

- **Файл:** `tools/pf_runtime/service.py`
  **Функции и диапазоны:**
  - `active_service` — 150–159
  - `cleanup_stale_runtime` — 162–175
  - `acquire_singleton` — 178–192
  - `RuntimeProcess.serve` — 405–417
  - `command_start` — 436–474

**Минимальная репродукция:**
1. В двух параллельных процессах/оконках вызвать `python tools/processforge.py runtime start --workplace <W>`.
2. Выполнить второй вызов до того, как первый записал `endpoint` в `runtime/pf-runtime/service.json` (первый пишет его после `ThreadingHTTPServer(...)` и только затем ставит статус `ready`).

**Влияние:**
Может быть запущено два экземпляра runtime для одного workplace (снятие `lock` как «устаревшего» у работающего стартующего процесса), что приводит к конкурентной работе двух фоновых демонов и неконсистентному состоянию runtime-кэша/health.

**Прямые доказательства из кода:**
- `active_service` считает процесс неактивным, если `endpoint` отсутствует, даже при валидном живом `pid` (`workplace/service.py:150-159`).
- `cleanup_stale_runtime` в таком случае удаляет `runtime.lock`, не гарантируя, что процесс действительно завершён (`workplace/service.py:162-175`).
- `command_start` вызывает `active_service` и затем `cleanup_stale_runtime` до форка нового процесса (`workplace/service.py:438-456`).
- `RuntimeProcess.serve` записывает `endpoint` только после успешного бинда HTTP-сервера (`workplace/service.py:411-417`).

---

## 2) `runtime stop` может пропустить работающий процесс с пустым/нечитаемым endpoint

**Severity:** LOW

- **Файл:** `tools/pf_runtime/service.py`
  **Функции и диапазоны:**
  - `active_service` — 150–159
  - `cleanup_stale_runtime` — 162–175
  - `command_stop` — 479–497

**Минимальная репродукция:**
1. Инициировать состояние, где `service.json` содержит живой `pid`, но `endpoint` временно пустой/неподходящий (например, в момент запуска/перехода состояния).
2. Вызвать `python tools/processforge.py runtime stop --workplace <W>`.

**Влияние:**
Команда завершения вернёт `RUNTIME: not running`, хотя процесс может ещё работать; это скрывает факт живого runtime и не отправляет ему `/shutdown`.

**Прямые доказательства из кода:**
- `command_stop` опирается на `active_service`; при отсутствии `endpoint` считает неактивным даже при живом PID (`workplace/service.py:481-483`).
- Стабильность определения активности тоже зависит от `endpoint` в `active_service` (`workplace/service.py:150-159`).

---

## Проверенные артефакты

- `tools/pf_runtime/host.py`
- `tools/pf_runtime/service.py`
- `tools/processforge.py`
- `tools/smoke_runtime_host_poc.py`
- `tools/smoke_long_lived_runtime.py`
- `tools/smoke_codex_exec_worker.py`
- `.pf/artifacts/runtime-general-line-20260814/runtime-correctness-report.md`
- `задания/process-forge-runtime-general-line-master-prompt.md`
