# Реализация нормализации Process / Stage

## Изменено

- Schema получила `evidence_definitions`, нормальный массив `process_transitions`, `automation_bindings` и совместимый legacy alias `technical_obligations`.
- Authoring normalizer/materializer теперь сохраняет Evidence, Stage required artifacts/evidence/parameters и automation bindings; legacy `gates` нормализуется только в `exit_gates`.
- `task-create --stage` записывает и проверяет durable assignment Stage.
- Runtime перестал угадывать названия стадий. Он берёт `assignment.stage`, затем явную `runtime_execution_boundary.stage_by_worker_status` конкретного Process; неизвестное состояние остаётся пустым.
- `work-state` строится из assignment/run facts, а projection остаётся только automation observation. Automation bindings больше не формируют второй blocker list.
- `process-supervisor` переведён на `automation_bindings`, имеет явную status-to-stage mapping и объявленные внешние inputs.
- Doctor проверяет Artifact/Evidence/Gate/automation binding ссылки, legacy aliases и opt-in `process_transitions[].route_id` против project route map. Route doctor также прогоняет JSON Schema.
- Добавлен user-process smoke с custom Stage IDs, Evidence, негативным Evidence случаем, opt-in Transition-to-Route failure/pass и `runtime-host work-state` без daemon.

## Проверки

- `python -m py_compile tools/processforge.py tools/pf_runtime/host.py tools/smoke_process_stage_contract_normalization.py` — PASS.
- `python tools/validate-process-forge-schemas.py` — PASS.
- `python tools/processforge.py process-doctor --project-root . --process process-supervisor --contract-only --force` — PASS.
- `python tools/smoke_process_stage_contract_normalization.py` — PASS.
- `python tools/smoke_process_authoring_materialization_parity.py` — PASS.
- `python tools/smoke_process_supervisor_tick.py` — PASS.
- `python tools/smoke_process_transition_handoff.py` — PASS.
- `git diff --check` — PASS.

## Review

Review worker `gpt-5.3-codex-spark` reported missing opt-in Transition-to-Route integrity and negative Evidence coverage. Both accepted and implemented. Требование всегда иметь `.pf/process-routes.yaml` отклонено: декларативный Process Transition может не быть Director/handoff route; map required only when Transition declares `route_id`.
