# Alpha4: dev-поставка и установка на устройство

Установка и функциональная приёмка установленного Core выполнены.
**Текущий MCP-host ожидает переподключения оператором**; его новый загруженный
код пока не принят. Work остаётся active/implementation, завершение не заявляется.
Точка продолжения: `alpha4-device-mcp-reconnect-20261023`.

Создан dev ZIP `processforge-1.3.0-alpha4-dev-20261023.zip` — точные байты
квалифицированного alpha4, без перепаковки исходников. SHA256:
`52474515eb6cbf59c7a307481a16ab717391c1616a6c924fd6d9156e8ee1aaf2`.
Dev sidecar отличается от публичного только archive.filename; его SHA256
`34da2f777f2eb8ff045c0f9b9b833d765e3657594aa91c4733116198cc476dd8`.
Исходный коммит — `7a8f726c320460ecfa99cd8dbf96ea8a631be00f`.
Публичные alpha4 assets/tag/feed и предыдущие архивы сохранены.

Штатное обновление `core-update-20261023T161353Z`: alpha2 → alpha4,
27 changed, 21 added, 1449 unchanged, ноль local conflicts/removals.
Все **1497** managed hashes совпали. Проверены 27 исходных backup preimages,
старый и новый control manifests. Конфигурация Workplace и неизвестные файлы
Core сохранены. `incomplete_update=false`, `repair=nothing_to_repair`.
Workplace doctor — **197 PASS**, без предупреждений.

Три guarded restart получили runtime_busy_or_activity_unknown. Полная расширенная
read-only проверка двух зарегистрированных проектов дала running=0, без issues.
После отдельного прямого разрешения пользователя выполнен **один** native restart
с --force; новый App Server ready. Повторного apply/force нет. Причина отказов
обычного guard не выдаётся за однозначно установленную; новая глобальная политика
или обход защиты по умолчанию не вводится.

Свежий полный pytest на копии всех точных installed managed bytes с исходными
тестами квалифицированного коммита: **732 passed, 7 skipped, 246 subtests passed in 315.26s (0:05:15)**.
Все **18 native smoke** завершились с exit 0, включая настоящий
новый fixture stdio MCP, init/refresh/search, scope/security и SQLite journal migration.
Все **7 CLI-вызовов физически установленного Core** дали
ожидаемые коды; mixed batch вернул ожидаемый 1 при сохранении успешных добавлений.
Проверены dry-run без записи, один selected-only проход в конце пакета,
сохранение прочих строк и отдельный manual full pass.

Матрица pytest включает cold constructors, backend Protocol, writer lock,
invalidation/retry/races, пустой корпус, безопасность/недоступные источники,
контекст без implicit indexing, schedule callable, batch ordering/duplicates/
cancellation/audit errors, journals backup/scan/CLI/service и accounting/usage.
Periodic scheduler и дополнительные БД не реализованы в alpha4 и не заявляются.
Семь skipped сохранены. Наблюдённые warning records приведены в test-report.json;
исторические SQLite warnings не объявляются исправленными.

Живой installed CLI: context fresh/continue на исходном snapshot
`ctx-20261021-162229-c46ea2`; точный Work search ready,
Python query total=79. Байты всех наблюдённых файлов
индекса после context/search не изменились. Project-scoped index status отдельно
показывает отсутствующие derived project ресурсы; он не подменяет готовность
Work search. Два старых missing project coverage элемента не скрываются.

Ruff/format/strict mypy/Bandit из квалификации зачтены для неизменённых байтов;
production Python здесь не менялся. Установленные функциональные тесты выполнены
повторно зарегистрированным Python QA. Новые зависимости не устанавливались.
Scoped run-doctor: 18 PASS; capsule-doctor: 12 PASS; ноль warnings.
Конфигурация, foreign dirty source, прежние alpha3 assets/stable-feed перепроверены.

Actual MCP до переподключения отвечает fresh на том же snapshot, но его старый
процесс был запущен до apply. Это не доказательство загрузки alpha4. Точный handoff,
selectors и immutable capsule checksum находятся в mcp-reconnect-handoff.md и
continuation.json. После reconnect нужны actual process provenance, pf.context,
точная pf.work.state, поиск/resolve разрешённых ресурсов; затем финальный отчёт,
commit/dual push/readback и нативное завершение этой Work. Установку и forced
restart повторять нельзя. Legacy monitor cli_version остаётся отдельной старой
константой; канонический installed VERSION/manifest и version CLI — alpha4.

Зафиксировано 2026-10-23T16:39:44.209844+00:00.
