# Результат независимой remediations-review (`ledger-hooks-mcp-remediation-review`)

## Итоговый вердикт
**PASS** по целевым требованиям изоляции проектов, авторизации shutdown и журналирования событий;
**частичный резервный риск** — отсутствует доказательство production-ready подключения реального Codex lifecycle hook в рабочей конфигурации.

## 1) Изоляция между проектами (cross-project isolation)

- **PASS.**
- После правок маршрутизация по сессии идёт через Agent Ledger, а не из runtime-кэша:
  - `tools/pf_runtime/host.py:ingest_event` отклоняет события для известной сессии при попытке подать событие в другой проект; неизвестные сессии допускаются только для `agent.session.started`/`agent.session.resumed`.
  - `tools/pf_runtime/mcp_server.py` (`tool_result`) сначала получает проект по сессии через Ledger, затем при `project_root` проверяет совпадение `project_id`.
  - `tools/pf_runtime/service.py` HTTP-роуты `/project-state`, `/work-state`, `/resolve` также валидируют session→project через Ledger (`assert_session_project_scope`).
- Поведение сессий теперь соответствует запросу “только по легитимному проектному привязке сессии”.

## 2) Аутентификация shutdown-эндпоинта (daemon lifecycle safety)

- **PASS.**
- `tools/pf_runtime/service.py` защищает `POST /shutdown` общей авторизацией:
  - проверяется `Authorization: Bearer <token>` через `authorize()`.
  - без валидного токена возвращается ошибка до остановки daemon.
- Проверка в smoke-тесте подтверждает ожидаемый отказ `401` для неавторизованного запроса на `/shutdown`.

## 3) Результат live hook (Codex adapter)

- **PASS по функциональному поведению адаптера в smoke сценарии; с пометкой по эксплуатации.**
- `tools/pf_runtime/codex_hooks.py`:
  - переводит hook-события в `agent.*` события и старается доставить через runtime IPC;
  - при недоступном daemon делает fallback в core ledger (`host.ingest_event`).
- `tools/smoke_runtime_ledger_hooks_mcp.py` фиксирует успешную доставку hook-события (статус `delivered`) и сохраняет результат в `live-hook-after.json` / `live-hook-worker.txt`.
- Отдельное замечание: в артефактах отмечено, что полноценный proof через реальную конфигурацию hook-хауков пользователя не стартован автоматически в данном контуре (ручная/внешняя стадия).

## 4) Регрессионные доказательства после ремедиации

- Подтвержденный pass-комплект в артефакте:
  - `python -m py_compile ...` — PASS
  - `python tools/smoke_runtime_ledger_hooks_mcp.py` — PASS
  - `python tools/smoke_runtime_host_poc.py` — PASS
  - `python tools/smoke_long_lived_runtime.py` — PASS
  - `python tools/validate-process-forge-schemas.py --root .` — PASS
  - `python tools/validate-public-cleanliness.py --root .` — PASS
- Дополнительно:
  - `project-context-check --json` — `fresh`, policy `continue`.
  - Live-hook артефакты (`live-hook-after.json`, `live-hook-worker.txt`) отражают успешное выполнение smoke-потока.

## Рекомендуемая постановка итогового статуса
- **Рекомендую принять ремедиацию как технически закрытую по трем проверяемым критериям**.
- **Открыть отдельный follow-up только на эксплуатационный proof подключения реального Codex hooks-конфига в живом пользовател. окружении** (если требуется production assurance уровня “end-to-end”).