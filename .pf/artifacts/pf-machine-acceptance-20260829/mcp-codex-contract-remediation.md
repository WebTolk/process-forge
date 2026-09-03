# MCP Codex Contract Remediation

## Исправления

- `pf.context` возвращает bounded projection без полных assignment objectives, но сохраняет `derived_reports` и публикует `resources.authorized_knowledge_ids`.
- MCP tools имеют корректные annotations для read-only и mutating операций.
- Governed Codex worker получает `mcp_servers.processforge.default_tools_approval_mode="approve"`; иначе Codex с policy `never` видел PF tools, но запрещал вызовы.
- Добавлен реальный stdio smoke `smoke_mcp_codex_contract.py`; release-test catalog включает его.
- Стабильные MCP errors проверяются по коду без утечки абсолютных путей.

## Реальная проверка

- Fresh Codex process успешно вызвал installed `pf.context` и получил проект `plg-content-varreplace`, fresh snapshot, ready search и 27 knowledge ids.
- Implementation и assurance workers выполнили порядок `pf.context`, `pf.work.start`, `pf.resolve`, `pf.search` до filesystem inspection.
- `docs.joomla-toolkit:root` и `docs.joomla-core.v6-1-2:source-tree` разрешены через PF. Поисковый индекс не нашёл узкую статью, поэтому использован PF-resolved Joomla 6.1.2 source tree.
- После возврата `derived_reports` targeted regression, MCP contract и ledger/hooks MCP smokes прошли.

## Проверки

- `smoke_mcp_codex_contract.py`: PASS.
- `smoke_runtime_ledger_hooks_mcp.py`: PASS.
- `smoke_derived_report_stale_marking.py`: PASS.
- Финальный extracted archive release-test: PASS, 1105.41 s.

Внешний PhpStorm MCP на `127.0.0.1:64442` выдавал transport errors, но PF stdio MCP работал независимо.
