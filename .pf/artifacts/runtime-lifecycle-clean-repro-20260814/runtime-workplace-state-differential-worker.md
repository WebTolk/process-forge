# Сравнение `runtime` состояния (live workplace vs clean passing trace)

## Что прочитано
- clean trace: `.pf/artifacts/runtime-lifecycle-clean-repro-20260814/runtime-lifecycle-clean-repro.md`
- live runtime metadata (фактическое workplace): `D:\.agents\processforge-workplace\runtime\pf-runtime\service.json`
- live runtime lock: `D:\.agents\processforge-workplace\runtime\pf-runtime\runtime.lock` — отсутствует
- live runtime логи:
  - `D:\.agents\processforge-workplace\runtime\pf-runtime\logs\runtime.stdout.log`
  - `D:\.agents\processforge-workplace\runtime\pf-runtime\logs\runtime.stderr.log`
- служебные артефакты запуска: `.pf/runtime/agent-runs/runtime-lifecycle-clean-repro-20260814/runtime-workplace-state-differential/*.json`

## Фактический live снимок
- `status` в service.json: `stopped`, `health`: `stopped`
- `endpoint`: `http://127.0.0.1:8767`
- `pid`: `14328`, `instance_id`: `6f04fda425164bd18c73d3dfd1d2abd2`
- `workplace_id`: `processforge-workplace`, `workplace_root`: `D:\.agents\processforge-workplace`
- `runtime_version`: `1.0.0-poc`, `protocol_version`: `pf-runtime-poc-1`, `processforge_core_version`: `1.0.2`
- `created/started/updated`: `2026-08-14T06:08:11Z` / `2026-08-14T06:21:11Z`
- `runtime.lock` отсутствует, при этом в `service.json` остаётся `pid/endpoint` для остановленного состояния
- `runtime.stdout.log` содержит повторяющиеся `ConnectionAbortedError 10053` и ошибки `request.error` по путям `/work-state` и `/tick` (400 responses после ошибки клиента)

## Сопоставление с clean passing trace
| Поле/аспект | Clean trace | Live workplace | Разница |
|---|---|---|---|
| Инициализация | `T0-T1`: runtime dir absent/start called | Нет активного старта в текущий момент | Live снимок — финальное остановленное состояние, не стартовый этап |
| Статус после `runtime stop` | `T10/T11`: lock `{}`, `status: stopped`, `health: stopped` | `status: stopped`, `health: stopped`, lock отсутствует | Совпадает по смыслу с финалом clean trace |
| PID/lock | `T2/T6`: lock/pid живые (`pid 4920`) | lock отсутствует, `pid 14328` в stopped-метаданных | Различаются инстанс/время, live не активный |
| Endpoint | clean trace: `http://127.0.0.1:62604` | live: `http://127.0.0.1:8767` | Различие в адресе из-за другого workplace runtime |
| Workdir | clean: `C:\Users\...Temp\pf-runtime-clean-trace-...` | live: `...\.agents\processforge-workplace` | clean тест использует изолированный temp-workplace, live — постоянный workplace |
| Журнал | clean artifact: нет подтверждённых abort-ошибок клиента | live stdout: ошибки `WinError 10053`/400 на http-запросах | Новые клиентские/сокетные симптомы в live-среде |
| Контрактные поля | в clean `ready`/`started` и ingress-переходы проходят | live сейчас уже `stopped`, ingress невалиден для active-контекста | Разница в фазе жизненного цикла |

## Вывод по историческому симптомам
- Исторический симптом `runtime start -> session-register -> runtime is not running` в live сейчас не воспроизводится, потому что текущий runtime уже в `stopped` состоянии (без lock, без живого процесса).
- По факту, live snapshot представляет неактивный срез после нескольких остановок, а не чистый "ready-path" из baseline.
- В сравнении с clean trace значимая несогласованность для живого статуса: **различаются только данные окружения и фазa жизни** (изолированный clean-workplace vs постоянный workplace), при этом `status`/`health` соответствуют корректному остановленному состоянию.
- Дополнительно отмечен потенциально релевантный шум: в live runtime-логах есть `ConnectionAbortedError 10053` и 400 на `/work-state`, `/tick`, что может маскировать client-side интерпретацию readiness в отдельных сценариях.