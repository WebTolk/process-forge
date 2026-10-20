# Handoff: context parity fix -> следующая сессия

Objective: проверить реальный MCP/CLI после принятого исправления и подготовить
дальнейшее решение по выбранному оператором `1.3.0-alpha1`.

Current status: ограниченный source fix завершён нативно: run_completed,
run completed, assignment done, incomplete []; run-doctor PASS.

Exact completed identity (не resume):

- run_id: garage-pf-context-parity-20261020-diagnose-and-fix-pf-cli-mcp-context-co
- assignment_id: pf-context-parity-20261020-diagnose-and-fix-pf-cli-mcp-context-consisten
- context_id: pf-context-parity-20261020-diagnose-and-fix-pf-cli-mcp-context-consisten-capsule
- capsule SHA-256: 00344bd0fed9d8e68f3cc4049a4e0125d5411dc21fe92684f9c4c2910755ee1e
- source commit: 526c5d13e42e96693802760cce35fe896e208708

Input artifacts: .pf/artifacts/pf-context-parity-20261020/primary/delivery.md,
review-result.json, source-remotes.json, package.json, cumulative-source-summary.json,
version-assessment.md, prerelease-ordering.json, alpha-preparation-handoff.md,
lifecycle/evolve.json, run-doctor.json. Source commit доставлен в origin/dev и
gitverse/dev; полные SHA обеих веток прочитаны. GitVerse — только через существующий
GITVERSE_TOKEN, без credential-manager fallback и без секрета в URL/аргументах/logs.

Files changed: два Core owner файла project/source_check.py и snapshot_sources.py,
два тестовых файла tests/context_parity, EN/RU context-resolution docs, только четыре
собственные checksum rows. 16 pytest passed +4 subtests; Ruff/mypy/context smokes PASS;
независимое source review PASS.

Files not to touch: чужой dirty/staged слой, незавершённые OOP54-55, resource readers,
project/platform_roots.py, tools/processforge.py и python-core-structure docs этой
чужой пары. Они исключены из source commit и чистого пакета, байты сохранены.

Known issues: ложное raw расхождение official pack из-за LF/CRLF исправлено в общем
Core. Тот же исходный снимок ctx-20261020-072238-da5df2 не обновлялся; его SHA-256
bd7dc7f033fe9f95f4c6903ea168868251db7666ef536c12479f7bcae667a05a.
Source CLI fresh/ready/continue. С новым Core реальные source/installed DATA дают
одинаковую freshness; нативный CLI и долгоживущий in-process adapter согласованы
на fresh/fresh/stale/fresh. Это не приёмка настоящим подключённым MCP.

Действующий connected pf.context после source fix всё ещё сообщил stale/ask_operator.
Исправление к установленному Core в этой Work НЕ применялось. Runtime/MCP/host hooks
не устанавливались и не перезапускались. Оператор сообщил, что перезапустит сессию
для проверки MCP/CLI. Один restart не устанавливает новый код: сначала требуется
отдельный разрешённый native Core delivery конкретного нового пакета, затем реальное
переподключение хоста и чтение его provenance/context. Не повторять старый успешный
core-update-20261020T081547Z или завершённый App Server restart. Этот handoff не
предоставляет infrastructure authority и не заменяет новую ограниченную Work.

Пакет: .pf/artifacts/pf-context-parity-20261020/delivery/processforge-1.2.0-dev-20261020-context-parity.zip
SHA-256: acaa0ff8b3b8a368520a7a115e3db14efe45c74555425f74ea116d9dd9b36457
Размер: 2791108 bytes. Native pack из чистого Git checkout PASS, sidecar рядом.
По прямому указанию пользователя содержимое ZIP не открывать/не проверять и
release-archive-test не запускать. Контрольный пакет действительно 1.2.0 dev;
имя будущего релиза — 1.3.0-alpha1, он ещё не собран и не опубликован.

Required checks для actual MCP/CLI: свежий pf.context и точные provenance/module
roots загруженного Core; пара ответов по одному проекту, снимку и фактическим inputs;
freshness, resource readiness, execution readiness, policy/reasons; не подменять
новый connected host независимым stdio процессом. Не маскировать различие refresh.
Историческая карточка pf-cli-mcp-context-consistency-20261019 остаётся open/planning-only:
source реализация передана, actual-host критерий пока не закрыт.

Решение по alpha: сейчас NO-GO. ResourceVersionPolicy отбрасывает prerelease suffix
и считает alpha1/alpha2/final равными; нужна узкая задача с сохранением остальных
resource constraints. Cumulative source release-test: 70 PASS / 1 FAIL, остановлен
по fail-fast на missing pathlib.Path import в smoke_runtime_no_domain_file_patterns.py.
Файл не менялся этим fix (последнее изменение ae111ca51f00676ea41d043285ef3cd9b19c0992).
Непройденные сценарии и supervisor-stress не объявлять успешными. Подготовить
настоящие VERSION/release identity/changelog для 1.3.0-alpha1 после устранения
этих препятствий, не менять массово schema/process/startup-contract версии.

Next recommended action: начать с живых .pf/AGENTS.md, pf.context/source check,
данного handoff и Git; не создавать native continuation для завершённого run.
Оформить следующую узкую Work под фактически порученную проверку/доставку либо
подготовку альфы. Полный OOP epic и Core unit coverage остаются отдельными задачами.
Собственные raw evidence и воспроизведение сохранены под .pf/tmp/pf-context-parity-20261020
по retention.json; удаление по возрасту не разрешено.

## Дополнение после прямого поручения установить, 2026-10-20 16:54 +04:00

Исправление УСТАНОВЛЕНО на текущее устройство отдельной разрешённой Work.
Один native apply core-update-20261020T124659Z, source 526c5d13, 5 changed,
1458 managed verified, incomplete_update=false, repair nothing_to_repair,
doctor-workplace PASS197. Installed и source CLI оба fresh/ready/continue на
прежнем snapshot без refresh. Ранее записанное «Core не обновлялся» описывает
состояние до этого дополнения. Актуальная передача:
.pf/handoffs/pf-context-device-install-20261020.md.
Осталось пользовательское переподключение/новая сессия и actual connected MCP
сравнение. НЕ применять этот пакет повторно и не повторять старый update.
