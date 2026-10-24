# Alpha5 принята на устройстве после перезагрузки

Приёмка установленной `1.3.0-alpha5` завершена. Источник
`af68fecfc539959d2b732e45016f5d09a700ec3d`, native update
`core-update-20261024T010255Z`. Все 1500 managed hashes совпадают.

Реальный Runtime и фактически подключённый MCP загружены после установки и
сообщают одинаковые loaded/installed source/build. Runtime имеет согласованные
owner/lock/readyz, native authenticated ready status и работающий scheduler;
doctor подтверждает current build. MCP отдаёт provenance contract 2,
reload_required=false, fresh/continue context и valid/ready exact Work.
Work search/resolve покрывают все семь разрешённых ресурсов; negative resolve
возвращает resource_not_in_work. Workplace doctor: 197 PASS.

Приёмка опирается на прежние 858 passed / 7 skipped / 383 subtests и 8 native
smokes для тех же установленных байтов. В этом продолжении повторены нужные
проверки хешей, реальных процессов, access и сохранности. Конфигурация, индекс
поиска, главный Git index и защищённые чужие файлы не изменены.

Первое подробное наблюдение Runtime было degraded; следующий штатный запрос
вернул ready, scheduler_alive=true и отсутствие status/scheduler errors.
Причина промежуточного состояния не установлена; raw результаты сохранены.
Global derived search по-прежнему stale с coverage 5/7; Runtime session/work/
worker metrics остаются partial. Эти ограничения не закрыты данной приёмкой.

Старые report.md, device-acceptance-decision.json и immutable handoff сохраняют
контрольную точку до перезагрузки. Их актуализирующее решение —
[post-reboot-device-acceptance-decision.json](post-reboot-device-acceptance-decision.json).
Проверки — [post-reboot-test-report.md](post-reboot-test-report.md).
Продуктовый код и инфраструктура не изменялись; повторных apply/restart/force,
repair и context/index refresh не было. Широкие OOP-эпики этим не закрываются.
