# T10: implementation record

Реализованы tools/pf_runtime/monitor.py (bounded collector, общий lifecycle consumer, allowlist JSON, terminal rendering/loop), pure classify_lifecycle в service.py, команда monitor и logger bypass/smoke registry в tools/processforge.py, meaningful smoke_runtime_monitor.py, EN/RU runtime-monitor docs и ссылки из runtime-mcp, public checksum refresh.

Product scope — ровно девять файлов из preservation.py. Предыдущие изменения основного CLI и docs сохраняются точечными patch; originals/ содержит исходные bytes для проверки собственного diff. Никакого daemon endpoint, shared config, установки, обязательного процесса или модели не добавлено.

Разработка выявила Windows pipe encoding mismatch: renderer теперь автоматически использует ASCII при non-UTF-8 sink. Smoke fixture сравнивает видимые terminal cells, не невидимые trailing spaces; fake server допускает закрытие соединения при проверке timeout. Неверный аргумент diagnostic-sink в первом test draft исправлен на действующий enum и дополнен spy, запрещающим for_project logging для viewer.

Живое наблюдение: source command читает existing installed Runtime; ready может сочетаться с degraded/stale, cache_oversize показывает unknown. Никакой обход лимитов не включён. Actual Windows PTY с TERM=xterm-256color показывает обновления, переход свежести и штатный Q exit; transcript сохранён в windows-pty.json. Это запуск source viewer, не installed CLI update.

При первоначальной общей schema validation обнаружен старый дефект live events.ndjson: строка 34212, timestamp 2026-09-26T12:15:42, Extra data, SHA256 6f1fa1694252d1b08e1ac8351716ab6129f302a26135c6bd56d7b1466c088739; до начала T10. Runtime journal не менялся. Assurance должна отдельно подтвердить product-only fixture и сохранить этот FAIL, не назвать общий checkout полностью зелёным.

Handoff: завершить source smoke/regressions/schema/public-cleanliness/checksums и review; exact preservation и current source hashes записать в evidence. Public/install delivery вне scope; staged product fixture под .pf/tmp/t10-monitor-20260926 является durable private qualification input до отдельной уборки.
