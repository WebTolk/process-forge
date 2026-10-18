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
установки и изменяемых данных. Если настроены долгоживущие процессы PF,
оператору нужно выделить время для их остановки перед заменой и запуска
нужной версии после проверки. Файловая работа Garage не требует установки служб.

Если установленный Core уже содержит updater, постройте план для скачанного
архива. Перед apply прочитайте конфликты и объявленную миграцию workplace:

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

Существующие непустые NDJSON-журналы проектных событий и входящих хуков требуют
явного импорта в SQLite перед их использованием. Это отдельная операция:
замена файлов Core и обновление контекста её не выполняют. См.
[миграцию журналов SQLite](../../concepts/hook-journal-sqlite.md) и
[инструмент миграции](../../../tools/migrate-hook-journals.py). Сохраняйте
оригиналы; другие журналы NDJSON не становятся устаревшими только из-за формата.

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
