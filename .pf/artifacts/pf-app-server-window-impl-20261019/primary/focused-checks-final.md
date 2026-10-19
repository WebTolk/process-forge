# Итоговые целевые проверки primary

Дата: 2026-10-19. После финального изменения test worker (25 -> 27 методов)
повторены только затронутые canonical проверки. Повтор singleton вызван
неразрешённым сигналом sandbox: worker не смог подтвердить liveness своего child.
TEMP/TMP — собственный task scratch; исходный тестовый код не подменялся.

| Команда | Результат |
| --- | --- |
| python -B tools/smoke_server_operator.py | exit 0; 27 server-console tests; actual HTTP guards, force, owner/auth, launcher, readonly JSON PASS |
| python -B tools/smoke_runtime_mcp_autostart.py | exit 0; minimized/exact interpreter/refusal previews и Codex MCP contracts PASS |
| python -B tools/smoke_runtime_singleton_orphan.py | exit 0; live-orphan и concurrent startup protections, atomic publication/failure cleanup PASS |

Нативная liveness проблема worker sandbox в родительском окружении не повторилась.
smoke_server_operator вызывает новую smoke_server_console через существующий
canonical entrypoint. Никаких настоящих Task Scheduler команд или перезапуска
установленных служб. HTTP/native child fixtures изолированы и штатно завершены.
GUI minimization API покрыты mocks. Windows native refusal — отдельное evidence;
успешная реальная минимизация Windows classic/Linux X11 не заявляется.

После этих проверок 1395 записей public-view-manifest сверены с source ещё раз:
source_changed_since_public_freeze = [], единственное объявленное исключение —
tracked Git baseline .pf/process-forge.yaml вместо постороннего dirty override.
