# Dev-релиз установлен и проверен

2026-10-22. Версия 1.3.0-alpha1, исходный коммит
48985ffae9130d09e72ac8c9fd8e908cbb41aa3a. Пакет собран из чистого Git-кандидата;
незавершённый рефакторинг основного checkout в него не попал.

Архив: dist/processforge-usage-accounting-dev-20261022.zip, 1477 entries,
2852160 bytes. SHA-256:
f689b41d4a67d14d68d94d974c7e648c224841af1acd07e2d9f7242af0701d71.
Sidecar содержит точный source commit/tree и хеш каждого файла.

Проверки: schema, cleanliness, checksum и release-check — PASS. В чистом
кандидате прошли 68 usage-тестов/36 подтестов и четыре связанных smoke-проверки.
Native archive-test проверил состав/хеши и quick-набор в распакованном архиве —
PASS. Это dev-квалификация; полный stable/public release-набор не выполнялся.

Установка core-update-20261022T125025Z: добавлено 14, изменено 9, сохранено 1453,
удалено 0, локальных конфликтов 0. Девять backup preimages сохранены updater.
Все 1476 установленных managed-файлов совпали с манифестом; incomplete_update=false,
repair=nothing_to_repair. База учёта прошла integrity_check, её содержимое и три
проверенных конфигурационных файла сохранились при замене Core. Перед заменой
сделана резервная копия SQLite.

PF App Server штатно остановлен и запущен из обновлённой установки. Runtime
doctor — PASS, health=ready; director/inspector/ledger/metrics/projection — fresh/ok.
Temporary-files job пока unknown, поэтому полная готовность всех наблюдений
не заявляется. Workplace doctor: 197 PASS, 0 FAIL.

Установленный CLI прочитал три настоящих usage receipt: input=3673006,
output=43020, total=3716026; учтённое execution time=1414.7816799 s.
Два повторных импорта добавили ноль usage/activity facts и сохранили итоги.
Установленные модули драйвера дополнительно проверены на изолированном
синтетическом subprocess: 7+3 токена, корректные cache/reasoning, положительное
время и сохранённый exit=17. Тестовый workplace отделён от настоящей статистики.

Installed project-context-check и подключённый pf.context: fresh/continue,
snapshot ctx-20261021-162229-c46ea2. Существующие MCP host-процессы не
переподключались; свежий ответ контекста не является доказательством перезагрузки
их Core-модулей. Новая установка CLI и новый PF App Server проверены отдельно.
Native автосбор Kimi и полнота всех сессий устройства по-прежнему не заявлены.

Публичные evidence: build-record.json, archive-assurance.md, installed-hashes.json,
device-result.json, installed-functional.json. Private updater/monitor receipts,
SQLite backup и изолированный probe сохранены локально. Чистый кандидат оставлен
как квалификационное evidence. Задача завершается этим циклом установки.
