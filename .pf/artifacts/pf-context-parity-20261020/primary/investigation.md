# Исследование и влияние: CLI/MCP context parity

## investigation-report
Доказательства: baseline.json; полные private module/path receipts находятся в task scratch.
Один и тот же снимок ctx-20261020-072238-da5df2 / sha256:bd7dc7f033fe9f95f4c6903ea168868251db7666ef536c12479f7bcae667a05a.
Source project-context-check: fresh/continue. Installed project-context-check: stale/ask_operator, единственная причина source changed: official-pack-processforge-official-software-development-package. Реальный подключённый pf.context тоже stale.
Отдельные процессы установили фактические ROOT/module files. AST общий для legacy checker, SourceCheckService и SnapshotSourcesReader в обеих дистрибуциях.
Raw source SHA пакета: 9cfcce38538d006fd446d12d0eaa1cd5a29496004e4298034f1596858055c080 (62 CRLF).
Installed SHA: a9dd4ec5c0fa3f8aacc912d6b18877f0e7d67cbc4bc441cbdfd9cb149357d2de (LF).
После преобразования только CRLF -> LF SHA совпадает. Реального изменения содержимого пакета нет.
.git attributes требует LF; рабочая копия фактически w/crlf. Устанавливаемый Git/archive контент использует LF.
Это определённая причина текущего false stale; произвольные build/data различия не объявляются устранёнными.
Refresh/restart/Core apply при исследовании не выполнялись. Отсутствие прямой PID-provenance в текущем payload actual pf.context не восполняется утверждением о новейшем найденном процессе.

## Цепочка
CLI command / MCP host -> project_context_check_result -> _project_context_check_result -> ProjectSnapshotSourceCheckService.compare -> ProjectSnapshotSourcesReader.read/fingerprint -> FileDigestReader.sha256_file.
OfficialProcessPackReader.active_records выбирает фактический пакет своего distribution_root.
Общий checker сравнивает raw SHA из снимка с raw SHA текущей дистрибуции, не различая текстовое представление LF/CRLF.
В ветке source hash совпадает со снимком; в installed он иной. Интерфейсы не имеют отдельных правил freshness.

## impact-analysis
Вмешательство ограничить Context And Access / Knowledge And Resources: обнаружение источников и общая source-comparison политика.
Глобальный FileDigestReader, checksum inventory, approved evidence и capsule SHA обязаны оставаться байтовыми.
Не трактовать пробелы, комментарии, YAML keys/values, BOM или одиночный CR как игнорируемое изменение.
Сохранять raw fingerprints и их публичную структуру. Нормализованное сравнение можно применять только к конкретным active official-process-pack текстам после проверки фактических live bytes.
Project/workplace/override/process fingerprints остаются строгими.
Сохранить added/removed reasons и их порядок; не скрывать недоступность ресурсов, expiration, stale markers, current-access/identity guards.
Необходимы pure-Core регрессии и адаптерная проверка на одинаковых входах; source, archive-shaped, installed и connected-host доказательства разделены.
Риски: старый подключённый MCP не загрузит изменённый Python метод автоматически; любое обновление/reload требует отдельной delivery authority и реальной host-проверки.

## investigation-complete / impact-understood
Причина воспроизведена до продуктовых правок. Проверены owners и actual consumers через Serena, существующие Python и исходные архитектурные контракты.
Новая реализация не вводит transport-specific ветвей, кэша или фоновых услуг.

