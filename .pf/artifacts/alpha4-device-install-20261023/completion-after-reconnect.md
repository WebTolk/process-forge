# Alpha4: фактический подключённый MCP принят

Контрольная точка переподключения пройдена после прямого сообщения пользователя
о перезапуске сессии. Точная continuation alpha4-device-mcp-reconnect-20261023
возобновила прежнюю active Work с неизменной capsule832ba15e.

Actual MCP запущен после native apply и использует entrypoint установленного
Core. Снова совпали все1497 managed hashes; manifest.version=1.3.0-alpha4,
source.commit=7a8f726c320460ecfa99cd8dbf96ea8a631be00f.
Это проверка реально подключённого хоста, не нового fixture stdio.

Текущая hook-сессия Codex online. Actual MCP context fresh/continue и installed
CLI check fresh/ready на одном snapshot ctx-20261021-162229-c46ea2. Точная
Work valid/ready; её native MCP search ready, total79, verified7 resources,
80 documents; docs.python:root разрешён со status ready.

Три параллельных запроса первоначально получили60s timeout; receipts сохранены.
Последовательные actual MCP context/search/resolve прошли. Global project
search по-прежнему имеет две исторические missing derived project resources;
эта граница не скрыта и не подменяет успешный verified Work search. Контекст
не обновлялся, индекс не перестраивался.

В alpha4 всё ещё есть известная константа1.2.0 в фасаде/мониторе. Поэтому она
не используется как доказательство старого MCP binary: проверены фактический
entrypoint, время запуска после apply, весь installed payload и live вызовы.
Исправление источника identity выполняет отдельная текущая alpha5 R03 Work.

Повторного apply/restart/force не было. Прежние backup/preservation,732 pytest
tests/7 skips/246 subtests,18 native smoke и7 physical installed CLI probes
сохраняются для неизменённых байтов. Product code этой проверкой не менялся.
Native status installed, incomplete_update=false; Alpha5 пока не устанавливался.

Функциональная приёмка alpha4 завершена. Остались отдельный portable evidence
commit/dual push/readback и штатный release/evolve closeout этой прежней Work.
Подробный результат: connected-mcp-after-reconnect.json; raw process/context
proof хранится в private scratch. Старые report/handoff остаются историческими.
