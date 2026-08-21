# Исправление smoke-проверки capability waiver

Дата: 2026-08-21

## Причина

`project-init --apply` возвращает краткую YAML-сводку с `status: blocked` и
`doctor.status: fail`; полный текст диагностического сообщения в этот вывод не
входит. Полное сообщение о недостающих declarations является контрактом
отдельной команды `doctor-project`.

## Изменение

В `tools/smoke_doctor_project_capability_waiver.py` проверка первого вызова
`project-init` теперь подтверждает его документированный итоговый статус.
Проверка точной диагностики `capability registry declarations are missing`
перенесена на последующий неуспешный вызов `doctor-project`. До- и послеусловия
waiver не ослаблены: без waiver нужен `FAIL`, после активных waiver нужен
успешный doctor с предупреждением о явном runtime-access waiver.

## Проверка

- `python tools\smoke_doctor_project_capability_waiver.py` — PASS.
- `python tools\validate-process-forge-schemas.py --root .` — PASS.
- `python tools\validate-process-forge-checksums.py --root . --write` и
  `--check` — PASS.
- `git diff --check` — без ошибок (Git вывел только предупреждения о CRLF).

Независимый review принят в
`.pf/reviews/project-init-local-search-mcp-doctor-waiver-smoke-review-20260821.md`.
Его worker не смог выполнить smoke в собственной read-only временной среде;
это ограничение окружения подтверждено отдельным локальным успешным запуском.
