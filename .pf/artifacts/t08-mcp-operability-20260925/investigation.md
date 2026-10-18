# T08 — investigation / impact analysis

## Воспроизведение и причина

Source HEAD a180ad624442d4fbe8ac1710073ef7d4c44babc4. Source и installed называют себя 1.1.0, но bytes различаются. Installed CLI reproduces stale с единственной причиной project classification changed; source CLI fresh/ready. Подключённый MCP context/start даёт snapshot_not_fresh для того же ctx-20260925-140110-0dbc7c.

classifier-probe.py в отдельных Python процессах проверяет загруженный __file__, классификацию snapshot и рассчитанную классификацию. Полные sanitized результаты: classification-source.json и classification-installed-before.json. Classifier software-web.yaml у обеих копий SHA256 04e718bcfcee1e51f1dd2c86b692422b437ab6340d3096f407bcfedd8fa85848. Единственное расхождение — matched_rules[].source: installed software-web.yaml против source/snapshot packs/official/software-development/project-classifiers/software-web.yaml. Types, platforms, tags, confidence одинаковы.

Source tools/processforge.py SHA256 107786ac30026f3f60f1726ba841aaece5563d165e536a885351ac13b2a3f670, installed 15f629a271e9ae5999e3addd9cfbbd2368128fea530e6aeb65774483b0b014ff. Source project_classifier_source_label (~3560) введён c810381e2d7fa2ec21300d16b4f7f4d2b16aa797. Installed всё ещё использует basename для внешнего classifier. Freshness сравнивает весь classification; это ложный stale из-за старого provenance, а не изменение проекта.

## Транспорт / жизненный цикл

CIM показал MCP entry point D:\.agents\processforge\tools\pf_runtime\mcp_server.py, workplace D:\.agents\processforge-workplace; PID 15980 child of Python launcher 1604 (проверять заново перед lifecycle actions). Bootstrap загружает tools/processforge.py относительно собственной distribution и кеширует модули. Файлового обновления недостаточно для уже открытого клиента. Сырой полный command line/env не сохранялись.

## Проверки выполненные до ремонта

Exit 0 / PASS: smoke_classifier_distribution_parity.py, smoke_mcp_jsonrpc_validation.py, smoke_mcp_missing_session_diagnostics.py. Первая регрессия проверяет stable classifier source across two distributions и сохранение genuinely changed classification. Installed/live успех пока НЕ достигнут.

## Impact analysis

Причина лежит в доставке Core, новый дублирующий source patch не нужен. Штатный manifest-update заменит согласованную distribution; полный file-level impact будет рассчитан core-update plan до apply. Unknown/local state сохраняется, локальные модификации не форсируются. Same-version update проверяется хешами, не только VERSION. Optional Runtime нужно штатно остановить и затем вернуть; host-owned MCP обновляется через операторский restart сессии. План отката — ownership backup + control old/new manifests + журнал, без bulk overlay/runtime deletion.

Ни refresh старым installed, ни выключение freshness не применяются: они скрыли бы причину. Source CLI временно ведёт эту Work. Live MCP acceptance остаётся отдельным обязательным gate после restart.
