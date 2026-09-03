# Независимый code review: полнота conversation capture

**Результат: FAIL.** Raw-first и номинальный happy path работают, но реализация не выполняет обязательные границы безопасности и crash-recovery из test contract.

## Блокеры

1. **Security/privacy: FAIL.** `tools/pf_runtime/host.py:647-652` применяет лишь эвристический blacklist и не сверяет content с raw payload. Любая строка секрета/полного payload без четырёх маркеров и без распознанного absolute path проходит в transcript. Более того, `:678-699` для PF-worker проверяет только `run_id`/`task_id` (`:655-664`), не требует ожидаемый `source_session_id`, `native_event_type` или полный provenance. Следовательно, локально поданный envelope с существующими run/task может записать произвольный `system`/`user`, а `assistant` — при одном лишь `kind=pf_codex_exec_output`; это не fail-closed граница «только ожидаемый report».
2. **Idempotency/atomicity: FAIL.** В `tools/processforge.py:10589-10620` transcript line записывается до `emit_process_event`. При падении между ними повторная доставка находит `message_id` и возвращается из `:10561-10568` с пустым event, не восстанавливая отсутствующий `chat.message.recorded`. Поэтому atomic transcript/event effect и recovery-after-raw, требуемые контрактом, не доказаны и фактически нарушены.

## Проверенные требования

- **Raw-first: PASS частично.** `tools/codex_exec_worker.py:105-141` строит UTF-8 hash, отправляет raw `WorkerPromptPayloadSubmitted` до `subprocess.run` (`:215-221`) и останавливает PF worker при неaccepted/не одном receipt.
- **Collectible output и порядок: PASS для happy path.** `tools/processforge.py:17863-17940` читает только expected-report, сначала захватывает его одной assistant message (`:17922-17935`), затем вызывает `command_task_complete`, после чего emit `worker.run.collected`. stdout/stderr в этот путь не передаются. Однако это не снимает blocker 1: Host не требует, чтобы assistant envelope был именно этим событием.
- **Codex UserPromptSubmit: PASS.** `tools/pf_runtime/codex_hooks.py:96-115` создаёт derived user message только для непустого строкового `UserPromptSubmit`; lifecycle/tool hooks остаются только `derived_event` (`:21-25`, `:46-70`).
- **Регистрация/регрессия: PASS частично.** Smoke зарегистрирован в `tools/processforge.py:6587-6591`. `python tools/smoke_conversation_completeness.py` и `python -m py_compile tools/processforge.py tools/codex_exec_worker.py tools/pf_runtime/host.py tools/pf_runtime/codex_hooks.py` завершились PASS. Но сам smoke (`tools/smoke_conversation_completeness.py:40-77`) проверяет prompt replay, один unsafe content и lifecycle; он не покрывает worker input/output, foreign/missing session, forged provenance, interruption между transcript/event и конкурентный delivery, поэтому blockers не выявляет.

## Условие повторного review

Нужны строгий allowlist по `(provider, adapter, native_event_type, role, content_provenance)`, точная привязка PF session к run/task/attempt и recoverable/атомарный transcript+metadata-event protocol; затем расширенный smoke на указанные failure/concurrency случаи.
