# Доставка исправления и решение по альфа-релизу

## delivery-report

Исправление общей политики Core принято независимым ревью и доставлено в обе
ветки dev. Коммит: `526c5d13e42e96693802760cce35fe896e208708`.
Обе удалённые ветки прочитаны и подтвердили этот полный SHA; см. source-remotes.json.
GitVerse отправлен через существующий GITVERSE_TOKEN без сохранения секрета.
Семь собственных файлов отделены от незавершённых OOP54-55; чужой рабочий слой
и его checksum rows сохранены. Реальный индекс до и после source commit пуст.

Причина расхождения: снимок содержал raw SHA официального manifest с CRLF,
а установленная дистрибуция содержала тот же текст с LF. Общая проверка считала
это изменением источника. Теперь только active official-process-pack manifest
и classifier допускают эквивалентные LF/CRLF представления; фактическое изменение
текста, наблюдаемый drift между чтениями, добавление/удаление и остальные source
guards остаются строгими. Raw fingerprints и публичные CLI/MCP payloads сохранены.

Исходный снимок `ctx-20261020-072238-da5df2` не обновлялся:
`bd7dc7f033fe9f95f4c6903ea168868251db7666ef536c12479f7bcae667a05a`.
С исправленным Core исходные source/installed DATA дают одинаковый fresh результат.
Нативный CLI и один долгоживущий MCP adapter на равных входах прошли четыре фазы
`fresh -> fresh -> stale -> fresh` без обновления снимка.

## source qualification

- 16 pytest passed, 4 subtests; Ruff lint/format и mypy PASS.
- Три существующие context smoke группы PASS; независимое source review PASS.
- Checksum validation, release-check и native packaging preflight PASS на чистом
  принятом исходном дереве.
- Для накопленного состава дополнительно выполнен native release-test --public
  --fail-fast --trace-smokes с явными исключениями архивных проверок.
  Результат: 70 PASS, 1 FAIL, 589.185 s. Прогон остановился на
  smoke_runtime_no_domain_file_patterns: NameError, не импортирован pathlib.Path.
  Файл последний раз менялся в ae111ca51f00676ea41d043285ef3cd9b19c0992, не в этом fix.
  Остальные сценарии не объявляются пройденными; git diff --check затронутой области
  выполнен отдельно и прошёл. См. cumulative-source-summary.json.
- supervisor-stress не квалифицирован: public-проекция не содержит private
  .pf/dogfooding/run_dogfooding_tests.py. Код проверки не переносился из чужой области.

## package

Native release-pack успешно выполнился из чистого Git checkout точного source SHA.
Архив: `.pf/artifacts/pf-context-parity-20261020/delivery/processforge-1.2.0-dev-20261020-context-parity.zip`.
SHA-256: `acaa0ff8b3b8a368520a7a115e3db14efe45c74555425f74ea116d9dd9b36457`.
Размер: 2791108 bytes. Нативный sidecar создан рядом.
Содержимое ZIP не открывалось, не извлекалось и не проверялось; archive-test не запускался
по прямому указанию оператора. Это исключение не является блокером выпуска.
Это контрольный dev пакет с настоящей версией 1.2.0, а не переименованный alpha.

## release-readiness-decided

Решение: source fix READY; публикация `1.3.0-alpha1` сейчас NO-GO.
Имя альфы принято по последующему указанию пользователя. `1.3.0` обоснован
совместимыми функциональными и существенными внутренними улучшениями; публичные
CLI/MCP контракты должны сохраняться. См. version-assessment.md и SemVer 2.0.0.

Конкретные препятствия:

1. ResourceVersionPolicy при сравнении обновлений считает alpha1, alpha2 и final
   одной и той же версией 1.3.0. Probe подтвердил, что alpha2/final после alpha1
   не считаются новее. Нужна отдельная ограниченная задача исправления перед
   публикацией с обещанием штатных обновлений; см. prerelease-ordering.json.
2. Публичный source release gate не проходит из-за сломанного smoke сценария.
   Нужно исправить import и выполнить оставшийся суммарный прогон на принятом
   исходном кандидате. Текущее независимое ревью context fix этим не подменяется.
3. Приёмка настоящим подключённым MCP остаётся открытой: после source fix
   действующий pf.context на прежнем снимке всё ещё сообщил stale/ask_operator.
   Новый код не применялся к установленному Core и реальный хост не переподключался.
   Прежний успешный update сегодняшнего утра не повторять; нужен отдельный
   разрешённый native delivery этого пакета и затем наблюдение реального хоста.

Подготовка VERSION/release identity/changelog и alpha metadata нужна на следующем
кандидате; schema/process/startup-contract версии и исторические capsules не меняются
автоматически. Незавершённые OOP54-55 не входят в этот принятый состав. Полный охват
Core unit tests и завершение всего OOP epic не объявлены условиями первой альфы;
их пределы должны быть явно отражены в заметках к выпуску.

## delivery-profile-run-or-skipped-with-reason

Source delivery и native dev packaging выполнены. Установка Core, Runtime/MCP
reload и alpha publication пропущены: их authority не входит в immutable scope
этой задачи оценки. Правило .pf/AGENTS.md, startup contract пункт 8, запрещает
такие инфраструктурные действия обычной Work. Здесь нет approval request и нет
неявного разрешения на эти действия.

Историческая карточка pf-cli-mcp-context-consistency-20261019 остаётся planning-only
open: реализация передана этим successor, полная connected-host приёмка ещё не закрыта.
Она не редактировалась и не получала новых прав. Передача следующих действий:
alpha-preparation-handoff.md и .pf/handoffs/pf-context-parity-20261020.md.

Source Work завершает только принятую ограниченную область; alpha assets/tag/channel,
установленный Core и actual connected-host acceptance не объявляются доставленными.
