# T10: исследование и влияние

Текущий исходный код сохранён в originals/ до изменений. service.inspect_lifecycle:182 — единая классификация по lock/state, PID, readyz; process count не доказывает ownership. Выделить её чистую функцию и сохранить существующий результат регрессиями. service.status_payload:796 использует load_token, который при отсутствии token пишет новый файл; RuntimeProcess.status_payload:400 вызывает known_project_roots, active_worker_count и last_event по проектам. Поэтому этот путь не используется при постоянной перерисовке.

service.json содержит updated_at, identity, status/health, scheduler.jobs с last_run/last_result; он обновляется через save_service_state. /readyz возвращает только status/ready и не содержит identity. Можно подтвердить matching lock/state/PID и повторно проверить записи после probe, но нельзя обещать криптографическую проверку remote process identity. Endpoint должен быть только числовым loopback HTTP, без redirect/proxy/auth. Ошибка probe не является доказательством остановки процесса.

host.state_path:39 и remember_session:410: projects — registered handles, sessions — cache_only с last_seen_at. Это не авторитетный перечень active sessions/workers. Не сканировать project .pf или presence store для выдуманного global total. Work/worker/lease/event/MCP/hook activity без агрегатного контракта остаётся unknown; known registries показываются отдельно с cache freshness.

processforge.main:28153 оборачивает команды в optional diagnostic logger; viewer должен обходить эту write-capable operation wrapper как другие read-only diagnostics commands. command_runtime_status и существующие CLI/runtime commands сохраняют поведение. process_pid_running использует Windows tasklist без timeout: monitor нужен отдельный ограниченный PID probe, а не изменение общей проверки для всех запусков.

Влияние ограничено новым viewer, чистой общей lifecycle функцией, CLI wiring, tests/docs/checksums. No daemon endpoint, schema, lifecycle behavior, token/host cache mutation. Нет основания перезапускать installed Runtime. Общие процессы и старый public plan не меняются.

Tooling gaps: Serena не имеет Python language backend; выполнены целевые UTF-8 reads. Snapshot не выбирает Python toolchain contract; в общей toolchain registry доступны только PHP/JS. Проверки берутся из existing repo smoke/validation patterns, Python stdlib; новые runtime dependencies не нужны.
