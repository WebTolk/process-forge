# Dev-поставка и установка alpha4

Основание — прямое поручение пользователя установить alpha4 на это устройство,
при необходимости перезапустить App Server и проверить написанные функции.
Это новая Work; завершённые release/review Work не переоткрываются.
Контекст ctx-20261021-162229-c46ea2 fresh/continue. Assignment, stage и
неизменяемая капсула проверены; checksum
`sha256:832ba15e62fd4d52d29f36cb8c36e6c7be514f16144631b1bd3038da91701667`.
Работа артефактная: исходники и установленный Core напрямую не редактируются.
Установка и условный restart выполняются штатными операторскими командами,
явно перечисленными в execution_mode. Абсолютные private paths не публикуются.

Источники: package.json и release-readiness.json завершённой alpha4 Work,
локальные core-update-manifest.md и runtime-monitor.md. Проверенный source SHA
`7a8f726c320460ecfa99cd8dbf96ea8a631be00f`, архив SHA256
`52474515eb6cbf59c7a307481a16ab717391c1616a6c924fd6d9156e8ee1aaf2`.
Полные source/archive профили уже дали 274/274 и 272/272. Публичные assets
и тег неизменяемы. Отдельное имя dev-архива обозначает поставку на устройство;
его payload сохраняет точные квалифицированные байты alpha4.

Сейчас установлен alpha2, 1476 managed files, incomplete_update=false.
Существующий Runtime ready; его процесс и MCP стартовали до этой установки.
Новая CLI и новый App Server не доказывают перезагрузку существующего MCP-host.
Число cli_version в старом monitor не заменяет VERSION/Core manifest.

Порядок: сохранить baseline исходников, конфигурации и данных Workplace;
проверить ZIP/manifest и создать отдельный dev-пакет без перепаковки payload;
получить штатный read-only update plan; проверить отсутствие local conflicts;
однократно core-update apply --confirm с Workplace и backup; сверить все
managed SHA256, native backup/control, doctor, status и repair;
при необходимости выполнить guarded server restart и проверить fresh/ready;
выполнить полную приёмку alpha4 через установленный Core на изолированных
fixtures, проверить наблюдение настоящего Workplace и границу MCP;
оформить portable report, doctors, коммит/push доказательств в обе dev;
прочитать удалённые SHA и завершить Work штатными переходами.

Матрица функций: cold constructors; контекст/init/refresh/repair/search без
неявной индексации; общий maintenance owner для CLI/scoped refresh/rebuild/tick
и холодного scheduler callable; SQLite FTS5 backend contract, блокировка writer,
ошибки и восстановление, durable invalidation, пустой корпус и read races;
batch dry-run, success/partial/all-failure, duplicates, cancellation, audit retry,
единственный проход только успешных qualified IDs с сохранением прочих данных;
реальные CLI и fixture stdio MCP. Негативные/конкурентные сценарии исполняются
на fixtures. Реальная периодическая регистрация scheduler и новые БД не входят
в alpha4 и не выдаются за реализованные функции.

Native apply с отказом не повторяется вслепую: сначала status/journal/backup.
Restart не должен прерывать активные Work/работников; busy guard требует
проверки причины. Автозапуск, host hooks, конфигурация пользователя и службы
не переустанавливаются. Обновление MCP-host не подменяется отдельной stdio-пробой.
Если host требует переподключения оператором, сохраняется точный handoff.

Новый продуктовый код и тесты здесь не добавляются. Используются существующие
релевантные тесты квалифицированного Core, зарегистрированный Python QA toolchain,
native validators и installed smoke. Повтор полного 50-минутного archive-профиля
для тождественных байтов не требуется; installed-функции проверяются заново.
Продуктовые ошибки блокируют GO и оформляются отдельно без правки immutable assets.
Посторонняя грязная копия и предыдущие квитанции/архивы сохраняются.
