# Исправление governance для Codex workers

## Воспроизведение

Свежая implementation-задача Joomla-проекта запустилась через официальный `codex-exec` с `--sandbox read-only`, несмотря на writer ownership и разрешённые code/artifact changes. Новый PF MCP Python process был создан, но агент сначала прочитал глобальную Codex memory, затем начал filesystem discovery и не вызвал PF MCP.

## Исправление

- sandbox вычисляется из assignment: writer с разрешёнными code или artifact changes получает `workspace-write`, read-only worker сохраняет `read-only`;
- PF-managed Codex worker отключает внешнюю Codex memory через `features.memories=false`, чтобы immutable capsule и PF resources оставались первичным контекстом;
- при наличии workplace knowledge grants launch prompt требует порядок `pf.context`, `pf.work.start`, `pf.resolve`, `pf.search` до shell/file/memory discovery;
- недоступность PF MCP теперь должна завершаться blocked report без тихого filesystem fallback.

Реальная повторная попытка в Joomla-проекте является обязательным приёмочным критерием.

## Результат реальной приёмки

- Implementation worker начал с `pf.context`, `pf.work.start`, двух `pf.resolve` и `pf.search`, и только затем обратился к разрешённому Joomla 6.1.2 source tree.
- Независимый assurance worker повторил PF-first порядок и подтвердил Joomla API, пакет и тесты.
- PF MCP автоматически получает `default_tools_approval_mode="approve"`; без этого Codex при policy `never` видел инструменты, но блокировал вызовы.
- Драйвер доверяет hooks не безусловно: `--dangerously-bypass-hook-trust` добавляется только когда полный `.codex/hooks.json` содержит исключительно штатную команду текущего PF `codex_hooks.py`. Любой посторонний handler отключает автоматическое доверие.
- Реальный Codex-сеанс `01a04ce9-9f57-7ac3-a483-cd6935308a9f` записал `SessionStart`, `UserPromptSubmit`, `PostToolUse`, `SessionEnd`; ledger содержит check-in, heartbeat и check-out.

## Проверки

- `python -m py_compile tools/codex_exec_worker.py tools/smoke_codex_worker_governance.py`: PASS.
- `python tools/smoke_codex_worker_governance.py`: PASS, включая отказ доверять foreign hook.
- `python tools/smoke_codex_exec_worker.py`: PASS.
