# Handoff: завершённая dev-приёмка 1.2.0 -> дальнейшая поставка

Objective: завершить точную dev-поставку 1.2.0 / 8ea152b после фактического MCP reconnect.
Current status: все согласованные слои dev-приёмки PASS; actual connected MCP принят, context fresh, exact Work valid/ready, docs.python:root и search ready. Runtime ready, прежний post-update instance. Native release/evolve завершены: run_completed/completed, assignment done, blockers[]; task/run/continuation doctors PASS. Commit и полный readback двух dev-веток фиксируются в delivery-publication-20261018.json.
Input artifacts: .pf/artifacts/pf120-dev-release-20261017/report.md, actual-host-acceptance-20261018.json, acceptance-review-20261018.md, closeout-20261018.json, stages/release-delivery.md, stages/evolve.md; прежние source/archive/installed receipts сохранены.
Exact run: garage-pf120-dev-release-20261017-package-committed-work-metadata-projec
Exact assignment: pf120-dev-release-20261017-package-committed-work-metadata-projection-qu
Exact context: pf120-dev-release-20261017-package-committed-work-metadata-projection-qu-capsule
Capsule checksum: sha256:9b9b49dd8a156c764ef7517f8f96b5b3f164ae9ce3216cc94c3489c0beff46df
Native continuation: pf120-dev-mcp-reconnect-20261017 была resumed с точными selectors; теперь штатно возвращает work_is_terminal, для новой работы её не использовать.
Qualified source: 8ea152bfa6376a66fc87c7ed48d74eacc5c2ad41
Applied ZIP SHA256: e332a74de958b2daad9711644bd848a82d1024b83bd03c47537377a27884a7dc
Files changed: только собственные evidence/report/handoff и штатные lifecycle записи PF. Product payload не менялся.
Files not to touch: immutable capsules и stage inputs, unrelated dirty/staged files, private configuration/history; не повторять Core apply, app-server restart или refresh свежего контекста.
Known issues: bounded shutdown history/partial metrics и платформенные ограничения перечислены в report.md. Stable release не опубликован. resume-checkpoint.json хранит прежнее состояние и pins до обновления отчёта/handoff; они были проверены перед обновлением. Историческая версия документов доступна в commit2468038.
Required checks: native task/run/continuation doctors после closeout PASS; перед commit — скан собственного публичного evidence на private paths/credentials, после commit — parallel push и полный readback обоих dev SHA. GitVerse использовать через GITVERSE_TOKEN без вывода секрета.
Next recommended action: следующую stable-поставку или продуктовую задачу вести отдельной Work с точными границами. Существующие эксплуатационные ограничения остаются в report/evolve; текущая задача завершена.
