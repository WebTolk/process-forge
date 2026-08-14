# Независимый review: verification-state / current-work-state

## Вердикт

FAIL. В проверенном slice остаются 2 существенные проблемы: одна correctness-проблема даёт ложный `passed/current` после rebuild, вторая оставляет `pf.work_state` почти таким же тяжёлым, как rebuild.

## Findings

- `H1` Смена relevant inputs после `task.doctor.passed` может снова стать `passed/current` после удаления/пересборки projection, хотя verification не запускалась повторно. В `build_verification_state()` fingerprint собирается из *текущих* assignment/required outputs и выбранного события (`tools/pf_runtime/host.py:195-209`), а выбранное событие ищется только по `passed_event` / `failed_event` и `task_id` (`tools/pf_runtime/host.py:184-191`). Сам `task-doctor` пишет событие без снимка проверенных input digests, только `task_id` и `result` (`tools/processforge.py:19471-19476`). Это противоречит заявленному контракту, где stale должен переживать rebuild и зависеть от declared event id/payload плюс relevant required-output digests (`.pf/artifacts/verification-current-work-state-20260814/verification-state-design.md:50-60`, `.pf/artifacts/verification-current-work-state-20260814/implementation-report.md:17-27`). Сейчас stale ловится только сравнением сохранённой старой строки projection с заново вычисленной (`tools/pf_runtime/host.py:250-267`); если projection удалить и пересобрать уже после изменения output/assignment, новая строка строится на старом PASS-событии и новых файлах и выглядит `current`. Smoke это не ловит: после перехода в stale тест сразу rerun-ит `task-doctor`, а не проверяет stale-after-delete/rebuild (`tools/smoke_verification_current_work_state.py:75-82`), хотя такой сценарий был прямо в acceptance/e2e ожиданиях (`задания/process-forge-verification-current-work-state-detailed-master-prompt.md:926-935`, `:967-971`, `:1040`, `:1203-1204`).

- `M1` `pf.work_state` не делает “cheap freshness read”; он всё ещё выполняет почти полный пересчёт obligations на request path. `work_state_payload()` вызывает `stage_obligations_payload()` (`tools/pf_runtime/host.py:635-681`), а тот каждый read заново строит `current = {row["id"]: row for row in stage_obligation_rows(...)}` (`tools/pf_runtime/host.py:240-267`). `stage_obligation_rows()` проходит assignments, резолвит process, читает run state, required outputs и journal events (`tools/pf_runtime/host.py:119-145`, `:68-80`). Это расходится с целевым контрактом “read existing projection -> recompute only cheap freshness -> response” (`.pf/artifacts/verification-current-work-state-20260814/verification-state-design.md:56-60`, `задания/process-forge-verification-current-work-state-detailed-master-prompt.md:818-835`, `:1208`). Более того, собственный audit slice уже зафиксировал, что `runtime-host work-state` по времени почти равен `rebuild-projections` (`.pf/artifacts/verification-current-work-state-20260814/verification-current-work-state-audit.md:76-96`). Это не ломает correctness напрямую, но требование по read-path сейчас не доказано и фактически выглядит непройденным.

## Что не подтвердилось как дефект в этом срезе

- Heartbeat и `exit.json` не используются как proof verification: verification берётся только из durable `task.doctor.*` event (`tools/pf_runtime/host.py:184-209`, `tools/processforge.py:19471-19476`).
- Stage-name special case для verification не найден: декларация действительно задаёт `verification-state` через process definition (`processes/core/process-supervisor.yaml:118-131`, `schemas/process-definition.schema.json:290-305`).
- Перезапись semantic artifacts не обнаружена; smoke на это есть и код проекторов пишет только `stage-obligations.json` (`tools/smoke_verification_current_work_state.py:47-48`, `:92-93`; `.pf/artifacts/verification-current-work-state-20260814/implementation-report.md:29-36`).
- Явной cross-project leakage в reviewed path не увидел: session routing идёт через Agent Ledger binding и фильтрацию по `project_id` (`tools/pf_runtime/host.py:534-563`, `:598-611`, `:660`, `:676`).

## Итог

Срез нельзя принимать как полностью закрывающий задачу. Критичный блокер — отсутствие rebuild-stable authoritative verification fact: после изменения входов старый PASS может выглядеть текущим. Второй блокер слабее, но тоже реальный: `pf.work_state` пока не соответствует обещанному лёгкому read-path и по коду/аудиту остаётся почти rebuild-эквивалентом.
