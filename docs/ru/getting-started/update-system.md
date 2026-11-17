# Система обновлений

Команды предназначены оператору. Запускайте их из установленного дистрибутива
Python-окружением из [инструкции установки](installation.md). Workplace и
проекты должны находиться отдельно от заменяемого Core. Агент обычного
проекта не должен обновлять Core или чинить необязательную инфраструктуру
ради обхода затруднений в задаче.

## Найдите и проверьте обновление

Система собирает сведения о серверах, находит кандидатов, подготавливает и
проверяет артефакт. Поддерживаемое файловое обновление применяется только
после явного подтверждения:

```bash
python bin/pf.py update entity-sources rebuild --workplace <workplace>
python bin/pf.py update candidates refresh --workplace <workplace>
python bin/pf.py update candidates list --workplace <workplace>
python bin/pf.py update notifications list --workplace <workplace>
python bin/pf.py update changelog show --workplace <workplace> --candidate <candidate-id>
python bin/pf.py update stage --workplace <workplace> --candidate <candidate-id>
python bin/pf.py update verify --workplace <workplace> --candidate <candidate-id>
python bin/pf.py update apply --workplace <workplace> --candidate <candidate-id> --confirm
python bin/pf.py update rollback --workplace <workplace> --candidate <candidate-id>
```

Для воспроизводимых локальных проверок используйте URL `file:///` для манифеста
и артефакта. Для удалённых серверов нужны HTTPS, доверенные сертификаты,
контрольные суммы sha256 и проверка источника релиза и миграционных указаний.
См. [требования](../requirements.md).

## Обновите установленное ядро

Не распаковывайте релиз поверх проектной `.pf/`. Сделайте резервные копии
установки и изменяемых данных. В Garage человек останавливает PF и остальных
писателей перед заменой и запускает нужную версию после проверки. В Forge этим
lifecycle единственного исполнителя PF управляет updater. Файловая работа
Garage не требует установки служб.

Распакуйте проверенный целевой архив вне установленного Core. Следующие команды
запускаются из распакованного дистрибутива с сохранённым исходным ZIP. Перед apply
прочитайте конфликты и объявленную миграцию Workplace:

```bash
python bin/pf.py core-update plan --core-root <installed-processforge> --archive <release-archive.zip> --workplace-root <workplace>
python bin/pf.py core-update apply --core-root <installed-processforge> --archive <release-archive.zip> --workplace-root <workplace> --confirm
python bin/pf.py core-update status --core-root <installed-processforge>
python bin/pf.py doctor-workplace --root <workplace>
```

Updater проверяет манифест управляемых файлов, создаёт резервные копии и
журнал операции. Если архив объявляет подходящую миграцию workplace, она
выполняется после Core. Независимые миграции workplace параллельно не
запускаются. Существующая пользовательская конфигурация — не повод повторно
вызывать `workplace-init`: команда предназначена для первичной настройки.
Если обновление прервано, изучите `core-update status` и используйте
предусмотренный сценарий `core-update repair`.

В старом публичном дистрибутиве 1.0.2 ещё нет такого updater. Для первого
управляемого перехода используется updater из распакованного целевого
дистрибутива с явными путями установленного Core и workplace. Исторический
[переход 1.0.2 → 1.1.0](../../../updates/migrations/1.1.0-stable-release.md)
описан отдельно; его утверждения о конкретной версии не гарантируют отсутствие
миграций в последующих релизах. Временные данные проекта храните под его
`.pf/tmp/`, отдельно от заменяемой установки.

## Проверьте каждый подключённый проект

После проверки Core и Workplace выполните оценку установленным CLI:

```bash
python bin/pf.py project-upgrade-check --project-root <project>
```

Команда использует установленный индекс обновлений и записывает
`.pf/artifacts/processforge-update-assessment.md`. Она не мигрирует
конфигурацию автоматически и не подтверждает перенос данных журналов.
До изменений прочитайте оценку и указания целевого релиза.

Старый проект с legacy-журналами отказывает обычной записи с
`storage_migration_required`. Новый проект сразу создаёт SQL-журналы и миграции
не требует. После остановки PF и остальных писателей выполните:

```bash
python bin/pf.py journal-maintenance import --project-root <project> --workplace <workplace> --apply
python tools/migrate-storage.py --project-root <project> --workplace-root <workplace> --apply --offline-confirmed --json
```

Первая команда импортирует события и raw-hook журналы, вторая переносит
execution snapshots и закрепляет стабильные UUID поддерживаемых хранилищ.
Это отдельные операции: замена Core и обновление контекста их не выполняют.
Для продолжения прерванной второй команды повторите точные корни с
`--resume --offline-confirmed`. Сохраняйте исходные журналы, планы и backups.
Проверки, причины отказов и восстановление описаны в
[обслуживании SQLite-журналов](../concepts/sqlite-journal-maintenance.md).
Другие журналы NDJSON не становятся устаревшими только из-за формата.

После необходимых миграций обновите и проверьте текущий контекст:

```bash
python bin/pf.py project-context-refresh --project-root <project>
python bin/pf.py project-context-check --project-root <project>
python bin/pf.py doctor-project --project-root <project>
```

Существующие капсулы остаются привязаны к исходному контексту. Обновление
снимка не разрешает молча переписывать или расширять капсулы. Если требуется
передача работы, выполните её через управляемый Work. Индексы ресурсов
обновляйте по их текущему состоянию. Внутри проекта используйте
`python .pf/runtime/bin/pf.py` вместо пути launcher относительно дистрибутива.
