# Исправлено: релиз 1.3.0-alpha2

2026-10-22. Предыдущий dev-пакет был ошибочно обозначен alpha1. По уточнению
оператора версия повышена до **1.3.0-alpha2** в VERSION и существующем источнике
archive identity. Старые утверждённые отчёты, архив и update receipt сохранены
как история; текущая поставка их заменяет.

Исходный коммит: fe0f15072538fee9525792ae5b8c1e634b13a928.
Архив: dist/processforge-1.3.0-alpha2-dev-20261022.zip, 1477 entries,
2852154 bytes. SHA-256:
9f9506b3cb2321723e9bee6ff9ef50b71566895ebce9fb27af0195f665466220.
Sidecar, Core manifest, VERSION и чистый CLI согласованы на alpha2.

Прошли Ruff lint/format, scoped mypy, 17 существующих тестов выбора версий,
три связанных source smoke и native quick-проверка распакованного архива.
Побайтовое сравнение с ранее квалифицированным пакетом показало только четыре
ожидаемых изменения: VERSION, release_identity.py, checksum inventory и
генерируемый Core manifest. Поведение учёта не менялось.

На устройство применён core-update-20261022T162745Z: версия alpha1 → alpha2,
изменено 3 файла, сохранено 1473; новых/удалённых/локальных конфликтов нет.
Сохранены три backup preimages. Все 1476 managed-файлов совпали с новым манифестом.
Installed CLI показывает ProcessForge 1.3.0-alpha2, incomplete_update=false,
repair=nothing_to_repair. База учёта и три проверенных конфигурационных файла
сохранились при замене; SQLite backup и integrity evidence остаются локально.

PF App Server штатно перезапущен; Runtime doctor PASS, health=ready. Workplace
doctor: 197 PASS, 0 FAIL. Данные трёх настоящих usage-записей по-прежнему дают
3716026 токенов; два replay не добавили записей и не изменили итоги. Изолированный
synthetic probe установленного драйвера прошёл, включая сохранение exit=17.

Контекст installed CLI и подключённого MCP — fresh/continue на прежнем snapshot.
Существующие MCP host-процессы не переподключались; их загрузка нового Core
не объявляется подтверждённой. Native автосбор Kimi и полная stable/public
квалификация также не входят в эту узкую dev-коррекцию.

Evidence: source-qa.json, build-record.json, assurance-report.md,
installed-hashes.json, device-result.json, installed-functional.json.
Source и артефакты отправлены в обе dev-ветки; последний artifact commit
фиксируется в результате доставки. После закрытия цикл останавливается.
