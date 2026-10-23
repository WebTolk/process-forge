# Alpha4 device: подключённый MCP

Установка выполнена **один раз**: `core-update-20261023T161353Z`, alpha2 → alpha4.
Все 1497 managed files совпали с manifest. 27 preimages и оба control manifests
проверены, configuration/unknown files сохранены. Doctor — 197 PASS,
incomplete_update=false, repair=nothing_to_repair.

Согласованный пользователем **один** native server restart --force выполнен;
новый App Server ready. Три предыдущих guarded отказа сохранены. Расширенная
проверка работников непосредственно перед restart: полное покрытие, running=0.
Ни apply, ни forced restart не повторять. Новых разрешений на force нет.

Dev ZIP — точные байты квалифицированного alpha4, SHA256
`52474515eb6cbf59c7a307481a16ab717391c1616a6c924fd6d9156e8ee1aaf2`.
Исходный коммит `7a8f726c320460ecfa99cd8dbf96ea8a631be00f`.
Публичные release assets/tag/feed сохранены.

Installed payload: 732 passed, 7 skipped, 246 subtests; 18 native smoke PASS,
включая fresh fixture stdio MCP. Семь физических installed CLI вызовов прошли
с ожидаемыми exit codes; batch selected-only/exactly-once/dry-run/partial/full
подтверждены. Живой installed context fresh/continue на прежнем snapshot,
Work search нашёл знания; байты индекса после чтения контекста/поиска неизменны.

Единственная оставшаяся функциональная граница — **actual connected MCP host**.
До обновления он был запущен в старом процессе. Переподключить ProcessForge MCP
в приложении; App Server restart этого не делает. Не менять host configuration,
не подменять reconnect новым fixture stdio и не повторять установку.

Точные selectors текущей Work:
- run: `garage-alpha4-dev-device-delivery-20261023-prepare-a-distinct-alpha4-dev`
- assignment: `alpha4-dev-device-delivery-20261023-prepare-a-distinct-alpha4-dev-packag`
- context: `alpha4-dev-device-delivery-20261023-prepare-a-distinct-alpha4-dev-packag-capsule`
- capsule checksum: `sha256:832ba15e62fd4d52d29f36cb8c36e6c7be514f16144631b1bd3038da91701667`

Work остаётся active/implementation. После переподключения проверить новый PID
и время запуска actual MCP, fresh pf.context на том же snapshot и точную Work,
pf.work.search/resolve по разрешённым знаниям; сопоставить с installed CLI.
Затем оформить финальные report/quality/doctor/preservation, доставить собственные
portable доказательства отдельным коммитом в обе dev, прочитать оба SHA,
завершить эту Work штатно и остановиться. Чужую работу и исходники не менять.

Raw outputs, original manifest, native commands and before/after observations
retained privately under this engagement's project scratch. Public receipts
 находятся рядом с этим handoff. Нельзя переоткрывать terminal alpha4 release Works.
