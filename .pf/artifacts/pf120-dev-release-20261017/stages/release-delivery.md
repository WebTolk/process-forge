# Release delivery: dev-кандидат 1.2.0 принят

Status: ready. Primary / release-engineer, 2026-10-17 20:38 UTC.

Delivery requirement: один согласованный private dev candidate с source/archive/installed/Runtime/actual-connected-MCP доказательствами; публичный stable release в этот scope не входит. Source 8ea152bfa6376a66fc87c7ed48d74eacc5c2ad41, ZIP e332a74de958b2daad9711644bd848a82d1024b83bd03c47537377a27884a7dc.

Delivery profile completed: clean native pack/checksum -> complete final consumer public suite -> native one-time Core apply -> controlled app-server restart -> installed CLI/manifest/HTTP/SQLite/independent-MCP acceptance -> actual connected-host acceptance after reconnect. Apply/restart/refresh не повторялись. Текущий Runtime ready; config/history preserved. Последний actual MCP gate PASS, context median 2.021 с после warm-up. Все обязательные delivery действия выполнены.

Release readiness decision: dev candidate accepted on this device. Stable tag/feed/assets not_applicable for this dev-only Work; отдельная публикация stable требует самостоятельной приёмки точной стабильной поставки. Известные эксплуатационные и платформенные ограничения перечислены в report.md, не преобразованы в PASS.

Evidence: ../report.md, ../archive-identity-final.json, ../archive-public-full-final.json, ../apply-summary.json, ../installed-integrity.json, ../installed-checks.json, ../runtime-http.json, ../installed-mcp.json, ../actual-host-acceptance-20261018.json, ../acceptance-review-20261018.md. Исторический checkpoint сохранён; актуальный handoff — .pf/handoffs/pf120-dev-release-20261017.md.

Handoff: complete native evolve, task/run/continuation doctors and scoped dual-remote evidence delivery. Сохранить immutable capsule и unrelated files; terminal Work не возобновлять. Следующая продуктовая или stable-задача должна иметь отдельные точные scope/Work.
