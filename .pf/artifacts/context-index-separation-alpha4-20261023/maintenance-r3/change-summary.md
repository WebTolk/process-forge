# Результат реализации maintenance R3

Единый `WorkplaceIndexMaintenanceService` переиспользует существующий `ResourceSearchIndex` без второго engine/DAL. Фактически используемый `ResourceIndexBackend` описывает только refresh/rebuild/maintenance_tick; default factory — существующий SQLite backend.

`.run()` читает текущий workplace catalogue на каждом вызове и возвращает schema1 `pf.search_index.maintenance`: scope workplace, project_count=0, results и относительный report. `.run_scoped()` принимает исходный project snapshot, не загружает общий каталог, не изменяет разрешённые ресурсы и возвращает исходный backend payload/exception. Через него переведены все три mutating search-index CLI adapters, с прежними constructor parameters, freshness guards, flags и stdout/exits.

Все эти операции используют общий OS-owned nonblocking lock. Running фиксируется до backend, required report — до complete; текущий JSON и history receipts публикуются через fsync/atomic replace. Process death освобождает lock, durable running остаётся incomplete; следующий явно разрешённый workplace pass повторяет обслуживание. Project pass не снимает running/failed/unavailable workplace state. Raw exceptions, абсолютные source roots и произвольные backend diagnostics не попадают в новые public/durable payloads.

Новый adapter/parser требуют отдельного explicit workplace target и apply. Main registration и замена его бывшего maintenance shim принадлежат primary. Runtime/timer/job loop не добавлены. Default composition не импортирует Main или Runtime.

Архитектурное соответствие для последующего independent review: D01/D02 — общий owner и настоящий узкий backend port; D03/D04/D05 — холодные explicit factories, snapshot/catalogue и lock живут в операции; D06/R04/R05 — supplied project snapshot не расширяется до workplace; D07/R07/R11 — required durable writes, crash-releasing lock и отдельная попытка retry; D09 — обычные Python modules/Protocol; D11 — bounded consumer migration. R01/R02/R03 — assignment/capsule/process/lifecycle не изменялись; R06 — новый вызов перечитывает catalogue; R08/R09 — trust, provider admission и Runtime/Ledger роли не менялись; R10 — disjoint owned files и один writer; R12 — portable safe diagnostics. D08/D10 не затронуты. Это mapping реализации и fixture evidence, не самостоятельная независимая архитектурная приёмка.

Проверено: собственный stdlib runner, 24 unittest, 0 failures/errors; AST/compile семи Python-файлов. Python 3.14.3 / SQLite 3.50.4. Подробности и hashes кандидата — `stdlib-checks.json`, тестовый вывод — `stdlib-output.txt` рядом.

Ограничения: это source/fixture evidence, не независимое review, registered pytest/Ruff/format/mypy/Bandit, archive/installed/connected/live acceptance. POSIX lock branch не исполнялся. Existing engine rebuild удаляет derived DB; engine уже пропускает некоторые ошибки чтения файлов и возвращает failed_file_count=0. Компонент честно обрабатывает возвращённые/raised failures, но полноту прочтения каждого файла это не доказывает. Изменение engine вне owned scope, primary/reviewer должны оценить этот остаток до общей приёмки.

Начальный TemporaryDirectory fixture-прогон получил WinError 5 из-за режима создаваемых Python 3.14 каталогов в sandbox; обычный mkdir внутри own scratch позволил выполнить проверки без изменения permissions. Generator lock также был исправлен после обнаруженного frozen LocalSearchError traceback regression; исходное исключение теперь сохраняется.

Автоматическая проверка отклонила cleanup-команду начальных scratch fixtures: «blocked by policy». Удаление не выполнено; они сохранены как evidence.
