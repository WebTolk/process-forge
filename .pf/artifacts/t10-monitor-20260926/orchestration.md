# T10: первый локальный терминальный монитор

Поручение: пользователь сказал «Продолжи» после перечисления оставшихся направлений и ближайшего T10. Выполняется первый законченный срез: read-only viewer существующего Runtime. Старый proposal и уточнение remote-web служат входом; нынешнее поручение разрешает этот ограниченный implementation scope, не массовое внедрение всех предложений.

Work: garage-t10-pf-vision-follow-up-implement-the-first-local-read-only-termi. Assignment: t10-pf-vision-follow-up-implement-the-first-local-read-only-terminal-mon. Capsule SHA256 6fb471b0e5f7ec47533c9acc17a18ef1cd262dd6ccb3cb79dd4044ebd0fe2cf4, intent 77db7e2dd73d52c70efc4ad8d7d431247d38c1cb12fa78efcb75bf844ac7e2dd. Snapshot ctx-20260925-140110-0dbc7c fresh. Process software-feature-development@1.1.0, все девять стадий, single agent.

Generated capsule содержит пустые worker file grants и allowed_actions read. Они не дают worker права писать: worker не запускается, capsule не расширяется и не пересоздаётся. Primary agent выполняет явно порученную пользователем разработку, execution_mode допускает code/artifact changes, review required. Собственный точный file scope фиксируется ниже и в scope. Это не выдача новых worker полномочий.

Разрешённые primary changes: tools/pf_runtime/monitor.py, ограниченное выделение общей lifecycle классификации в tools/pf_runtime/service.py, CLI/registry в tools/processforge.py, tools/smoke_runtime_monitor.py, docs/concepts/runtime-monitor.md, docs/ru/concepts/runtime-monitor.md, ссылки в существующих runtime-mcp.md EN/RU, checksums/processforge.sha256. Governance: собственные .pf/artifacts/t10-monitor-20260926/**, log/handoff и нормальные generated Work records. Сохранить прежние dirty edits; baseline до product changes. Временные репозиторные файлы только .pf/tmp.

Не входят: управление/перезапуск/установка действующей инфраструктуры; pf-server executable, tray, safe-stop UI; browser/remote web; egress engine; public release. Тесты используют изолированные временные fixtures, live окружение только читается. Никаких скрытых start/repair или auto-refresh context.

План: scope → source investigation → domain metrics/ownership → architecture/implementation plan → module/CLI/docs/tests → review/quality/live read-only observation → source delivery with explicit installed boundary → evolve/handoff. Optional browser/install/public release проверки отмечаются not_applicable с причиной, а не пропускаются молча.

Tooling: реальный PF context/search/resolve/start/state; search authorized coverage empty, resolve доступен. Serena Python symbols unavailable (Active languages: []); targeted rg/UTF-8 reads используются как fallback. Snapshot не выбирает platform/toolchain contracts; глобально доступны PHP/JavaScript contracts, к Python standard-library viewer они не применимы. Локальные исходники/EN/RU docs являются первичным reference; внешняя библиотека не вводится.
