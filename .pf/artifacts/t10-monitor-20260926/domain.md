# T10: состояния и метрики

Owner: matching instance_id и PID в lock/service плюс живой PID; найденный процесс или port сами по себе owner не создают. Lifecycle: ready/starting/stopping/failed/orphaned/stopped/not_running/stale; неизвестность чтения/PID/probe — отдельный unknown. Monitor использует ту же чистую lifecycle классификацию, что service, и может только понизить доверие при отсутствующих доказательствах.

Readiness /readyz показывает ответ существующего локального endpoint, не качество scheduler/MCP/hooks. Health берётся из сохранённого state и всегда сопровождается возрастом. state.updated_at старше 15 секунд — stale, отсутствующее/неверное/будущее время — unknown. Это порог свежести наблюдения, не обещание cadence daemon. Состояние ready при старом state отображается lifecycle ready, freshness stale и health unknown, а не общий green.

Scheduler rows отражают last_result/last_run конкретного job, не live thread probe. При устаревшем timestamp last result сохраняется как historical/cached, не утверждается current. Job names ограничены и защищены от terminal control sequences. Host projects/session records называются registered/cached counts; отсутствие/невалидный cache даёт null, а не 0. Activity workers, Work waiting, leases, event rate/backlog, MCP/hooks остаётся unknown в первом срезе: нет bounded authoritative aggregate source. Отсутствие событий не означает idle.

Чтение не создаёт workplace, token, logs, diagnostics или projections. Ошибки имеют finite reason codes, сырые payload/exception/project paths/prompt/chat/token не рендерятся. На экране допускается выбранное пользователем имя workplace, версия из validated version field и PID. JSON содержит такую же allowlist проекцию, не raw service dump.

Viewer lifespan независим: никакого daemon subprocess/start/stop/tick; q/Esc/Ctrl+C завершают только монитор и восстанавливают терминал. Missing/stopped daemon — нормальное наблюдаемое состояние, не повод repair. Код 0 означает полученную проекцию, включая unknown/offline; 2 — ошибка CLI arguments, 1 — неожиданный внутренний отказ viewer. Raw ошибки не попадают в stdout.
