Сделано.

- Изменение внесено: в `[tools/processforge.py](/D:/Dev/process-forge/tools/processforge.py)` добавлен `ReleaseCommand`:
  - `smoke_central_event_replay`
  - `python tools/smoke_central_event_replay.py`
  - timeout `180`

- Проверка выполнена (одна выбранная проверка):
  `python tools/processforge.py release-test --root . --only smoke_central_event_replay --no-clean`
  Результат: `PASS`, `11.87s`.

- Отчёт записан: `[session-replay-release-registration-report.md](/D:/Dev/process-forge/.pf/artifacts/central-agent-event-ingress-20260814/session-replay-release-registration-report.md)`.

- Остаточные риски:
  - Нестабильность не ожидается, но запуск с `--no-clean` пропускает step очистки release-артефактов; при сценарии полного релизного прогона это несущественно.
  - Изменение затрагивает только реестр smoke-команд и не влияет на публичный CLI/логику теста.
