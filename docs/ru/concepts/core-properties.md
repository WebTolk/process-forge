# Свойства Core

`processforge_core.common.properties` владеет идентичностью метаданных выбранной
поставки Core. CLI, Runtime, монитор, MCP и Host используют этого владельца через
существующие поля версии. Внутренний объектный контракт относится к постепенному
развитию [структуры Python-ядра](python-core-structure.md); весь OOP-рефакторинг
остаётся отдельной программой, стабильный публичный transport API не добавляется.

## Владение и композиция

Один связный модуль содержит четыре типа:

| Тип | Обязанность |
| --- | --- |
| `CoreIdentity` | Frozen value со строками `version`, `build_id`, `source_commit`, `source_kind`, `status` и `reason`. |
| `CoreIdentityReadPort` | Узкая структурная зависимость: `read() -> CoreIdentity`. |
| `DistributionMetadataReader(distribution_root)` | Ограниченное чтение метаданных одной явно выбранной поставки. |
| `CoreProperties(reader)` | Захват загруженного значения и отдельные актуальные наблюдения диска. |

Штатная композиция приложения использует общую фабрику:

```python
from processforge_core.composition import build_core_properties

properties = build_core_properties()
loaded = properties.loaded
installed_now = properties.installed()
```

При первом вызове фабрика под lock создаёт один объект properties. Корень
определяется по её собственному модулю Core в структуре поставки с `src/`.
CLI facade вызывает фабрику при boot; `RuntimeBootstrap.properties` возвращает
тот же объект. На время жизни приложения сохраняются неизменяемая идентичность
и reader выбранной поставки, без текущего проекта, Work, grants и документов
запроса. Для этой обязанности не вводятся DI-контейнер или service locator.

Библиотечный код и fixtures могут передать reader без загрузки CLI или Host:

```python
from processforge_core.common.properties import (
    CoreProperties,
    DistributionMetadataReader,
)

# selected_root — явно переданный корень поставки.
properties = CoreProperties(DistributionMetadataReader(selected_root))
```

`CoreProperties.from_distribution(selected_root)` собирает тот же concrete
reader. Конструкторы и типы не выдают права на файловую систему или Work.
Чтение свойств не запускает Runtime/MCP, не обновляет контекст, не обращается
к сети и не сканирует Git status/history.

## Загруженная идентичность и наблюдение установки

`loaded` захватывается один раз при создании сервиса. Обновление файлов на диске
не заменяет frozen value. Каждый вызов `installed()` перечитывает метаданные
того же привязанного корня. Новый сервис может захватить обновлённые метаданные;
повторный вызов `build_core_properties()` в существующем процессе возвращает
первоначальный объект.

Текущий каталог и соседние установки не выбирают поставку общей фабрики.
После переноса всей поставки новый процесс использует корень перемещённого
модуля. Уже созданный reader сохраняет исходный resolved root: он не следует
за перемещением каталога и не ищет другую установку. Эта семантика сама по себе
не доказывает реальный restart, reconnect или update.

## Происхождение метаданных и ограничения

`VERSION` владеет release label, включая prerelease/build suffixes. Reader
читает ограниченные UTF-8 данные: до 1 KiB для `VERSION` и 8 MiB для
`processforge-core.manifest.json`. Присутствующий manifest должен пройти прежнюю
native file-map validation и согласоваться с `VERSION`; повреждение метаданных
не маскируется release-литералом или Git ref.

| Источник метаданных | Идентичность |
| --- | --- |
| Пригодный Core manifest | `source_kind="manifest"`; `build_id="manifest:sha256:<digest>"` — хеш точных байтов manifest; `source_commit` — корректное шестнадцатеричное значение `source.commit`. |
| Manifest отсутствует, Git HEAD/ref доступен | `source_kind="source_checkout"`; `source_commit` — наблюдаемый ref, `build_id="git:<commit>"`. |
| VERSION корректен, build/revision недоступны | Версия сохраняется; неизвестные поля равны `unknown`, status — `partial`. |

Git observation ограничено чтением и поддерживает detached HEAD, worktree
pointers и packed refs. Существование commit object, достоверность происхождения
и отсутствие изменений рабочего дерева не проверяются. Хеш manifest относится
к байтам метаданных, включая сериализацию и timestamp. Поэтому одинаковые
release labels могут иметь разные build IDs. Ни этот хеш, ни Git ref не
проверяют содержимое payload-файлов; hash qualification архива/update остаётся
отдельной проверкой по контракту [Core update manifest](core-update-manifest.md).
`source_kind` описывает источник наблюдаемых метаданных, а не приёмку архива
или установки.

`status="ready"` означает получение полей метаданных, reason пустой.
`partial` сохраняет известные поля и объясняет недоступное происхождение.
Непригодные обязательные метаданные дают `unknown` вместо угаданной версии:

| Условие | Ограниченная причина |
| --- | --- |
| VERSION отсутствует или некорректен | `version_missing` или `version_invalid` |
| Manifest некорректен или расходится с release label | `manifest_invalid` или `version_manifest_mismatch` |
| Метаданные превышают лимит или не читаются | `metadata_too_large` или `metadata_unreadable` |
| VERSION/manifest изменились при проверочном перечитывании | `metadata_changed` |
| В manifest нет пригодной source revision | `source_revision_unavailable` (`partial`) |
| Нет manifest и пригодной Git revision | `build_metadata_unavailable` (`partial`) |

Value не содержит private roots и текста исключений. Причины доступны через
объектный контракт; ключи существующих transport schemas не добавляются.

## Независимые версии и адаптеры

| Существующая поверхность | Смысл |
| --- | --- |
| Release-строка CLI `version` | `loaded.version`; в прежнем выводе из трёх строк отдельно остаются Spec и Schema bundle. |
| Runtime/Host `processforge_core_version` | Загруженный Core release сообщающего процесса. |
| Runtime `installed_pf.version` | Актуальное наблюдение диска поставки, привязанной к вызывающему процессу. |
| Monitor `cli_version` | Загруженный Core CLI, выполняющей монитор. |
| MCP `serverInfo.version` и версия action discovery | Загруженный Core обслуживающего MCP-процесса. |
| `spec_version` и `schema_bundle_version` | Прежние версии specification/schema bundle, обе `1.0`. |
| Runtime `instance_version` / component version | Самостоятельная версия компонента Runtime, сейчас `1.0.0-poc`. |
| Версии протоколов Runtime и MCP | Отдельные compatibility contracts (`pf-runtime-poc-1` и `2024-11-05`). |

Текущий Runtime doctor сравнивает записанную версию Core с актуальной версией
установки. Такое сравнение версий не обнаруживает смену build при прежнем label;
build IDs объектного контракта остаются отдельными от существующих payloads.

Проверки исходников/imports, макет поставки с переносом, чистый release archive
из commit, установка на устройство и реальный connected host — отдельные
границы evidence. Наблюдение метаданных fixture не квалифицирует целостность
архива, сохранность данных устройства или restart/reconnect. Действующие
операционные контракты описаны в [модели Runtime](runtime-model.md) и
[release checklist](../../release-checklist.md).
