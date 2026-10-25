# Сбор хуков и жизненный цикл сессии

Размещение временных материалов и настройка уведомлений об их возрасте описаны
в разделе [временные файлы](../temporary-files.md). Уведомления не удаляют файлы.

Автоматические хуки агента учитывают итоговый режим проекта после наследования
настроек рабочего места. В кузне (`organized`) вахтёр обязателен. В гараже
(`simple`) хуки по умолчанию игнорируются; оператор может включить их через
PFConfig. Наличие запущенного Runtime не определяет режим проекта.

Значение рабочего места хранится в `configuration.yaml`:

```yaml
schema_version: 1
runtime:
  garage_hooks: false
```

Проект может переопределить его в `.pf/configuration.yaml`:

```yaml
schema_version: 1
runtime:
  garage_hooks: true
```

Отсутствие переопределения или `garage_hooks: null` означает наследование.
Глобально допустимы только булевы значения, в проекте — булевы или null.
Сохраняются существующее обновление конфигурации на лету и обработка ошибок
с последним корректным значением. Параметр действует только для гаража:
отключить им вахтёра кузни нельзя.

Используются существующие команды конфигурации:

```bash
python bin/pf.py config update --workplace <workplace> --key runtime.garage_hooks --value true
python bin/pf.py config update --workplace <workplace> --project-root <project> --key runtime.garage_hooks --value false
python bin/pf.py config delete --workplace <workplace> --project-root <project> --key runtime.garage_hooks
python bin/pf.py config read --workplace <workplace> --project-root <project> --key runtime.garage_hooks --json
```

Удаление ключа проекта возвращает наследование. Существующие параметры
`logging.raw_hooks` и `logging.events` независимо управляют дополнительными
записями после допуска хука. Явные операции Core/CLI, сбор отчётов работников и результаты Work
остаются доступны при выключенных автоматических хуках гаража.

Хук сначала обращается к аутентифицированному апп-серверу, при недоступности
использует тот же Host/Core через CLI. Отключённый гаражный хук завершается
до записи исходного хука, событий проекта, переписки, регистрации в Ledger
или отложенного содержимого. Ответ нейтральный: `{}` для Stop/SubagentStop
и пустой вывод для остальных проигнорированных хуков. Проигнорированный
SessionStart не сообщает агенту о привязанной сессии.

Для разрешённых хуков SessionStart автоматически регистрирует сессию,
а SessionEnd завершает её. Агенту не требуется ручной check-in/check-out.
Явно доверенный адаптер также может зарегистрировать неизвестную сессию
при первом разрешённом нетерминальном хуке: это покрывает перестановку
событий и включение сбора посреди сессии. Чужая или неоднозначная привязка
не заменяется; PF-работники сохраняют отдельные проверки задачи и попытки.
Идентификаторы событий и сообщений остаются идемпотентными, в том числе
при запоздавшем SessionStart.

Смена параметра автоматически не удаляет исторический буфер сообщений.
При разрешённом оператором обслуживании устаревшие сессии нужно отличать
от текущей работы и сохранять необходимую историю проектов.


## Полная эффективная конфигурация приложения

`ConfigurationProvider` возвращает полный неизменяемый `PFConfig`: metrics,
logging, temporary files, Garage hooks и database. Provider закрепляет явно
разрешённые device/workplace/project paths и уже авторизованный typed
`ProjectPFConfig` context. Он не обнаруживает enrollment и не интерпретирует
Work permissions. Routing выбирает host; Runtime, daemon и сеть не требуются.

Порядок: builtin → device → явно записанные workplace leaves → project →
authorized context. Отсутствующие workplace поля наследуют device. Явные false
и значения, равные defaults, перекрывают базу. Project/context null наследует;
прежний allowlist запрещает metrics overrides. Forge policy, capsule scope и
resource grants проверяются независимо и не расширяются настройками приложения.

Host вызывает `live.snapshot()` один раз на операцию и передаёт downstream
`ConfigurationProvider.pinned(snapshot.config, errors=snapshot.errors)` либо
его `current()`. `get(key)` читает полное effective значение. Consumers не читают
и не мержат YAML сами. Native worker transport, host builder и CLI routing
подключаются integration owner; snapshot не выдаёт body-read или policy grants
и не должен попадать в model prompt либо public status.

Default device file — Windows `LOCALAPPDATA/ProcessForge/configuration.yaml`
(fallback home/AppData/Local); POSIX absolute
`XDG_CONFIG_HOME/processforge/configuration.yaml` (fallback home/.config).
Relative env roots запрещены. Импорт/конструктор не выполняют stat/read/mkdir,
connect, scan или startup; первый snapshot — явное чтение. Missing files дают
typed defaults и не создаются чтением.

`ConfigSnapshot.explicit_keys` — внутренние dotted keys из тех же bounded,
validated YAML bytes, что дали model и revision. `schema_version` не override;
`database.profiles.<id>` атомарен, `database.defaults.<slot>` — leaf. Метаданные
не сериализуются в YAML. Device/workplace profile IDs должны быть disjoint,
даже при одинаковых definitions. Project/context разрешают только project scope
и не могут менять workplace_main. References/scope валидируются. Profile path
относится к authorized owner flow/workplace, не к каталогу device config; сам
профиль не предоставляет доступ к target.

`snapshot(refresh=True)` перечитывает только выбранные layers. Обычный snapshot
проверяет replacement signatures через bounded cache под lock. First invalid,
unsafe read выбрасывает прежний `ConfigurationError`; later invalid оставляет
last-valid model/presence/revision вместе и сообщает code в `ResolvedConfig.errors`.
Merge/policy errors не подавляются. Pinned refresh возвращает тот же snapshot
без I/O; CRUD и другие запросы не меняют уже начатую операцию. Mutable global
current-project отсутствует; requests/contexts/threads изолированы.

Прежний `resolve(base_path, project_path)` сохраняет двухслойный смысл positional
аргументов; `resolve(None, project_path)` использует builtins. Отсутствующий
project path создаёт только in-memory empty override. Workplace выбирается явно.

`database.driver` — необязательный sqlite/null selector без обязательных profiles.
`PFConfig.get('database.driver')` даёт sqlite при отсутствии; ProjectPFConfig —
override или None. `with_changes` и `ConfigService.reset` удаляют selector через
None, сохраняя profiles/defaults. Отсутствующая database не добавляется в старые
payloads. Прежний CRUD сохраняет материализацию старых полей; реально записанные
default-valued поля становятся explicit workplace overrides. Refresh не меняет
закреплённый store UUID/path: это отдельная maintenance обязанность host.
# Operation-local storage host

Полный merged PFConfig закрепляется на время выбранной native operation.
Вложенный вызов без device selector использует тот же snapshot и не перечитывает
default YAML. Storage host передаёт адаптерам только соответствующие выбранным
roots targets; выход из operation восстанавливает прежний context.

Cold factory не открывает БД, не создаёт guard или UUID. Неизвестная безопасность
до pending сохраняет поддержанный legacy route; после pending/binding требуется
точное восстановление либо отказ. Наличие factory не доказывает исключение старых
managed owners и не означает готовность installed automatic migration.

Выбранный device path сохраняется отдельно от полного pinned PFConfig. Вложенные
event/accounting/first-write hosts используют host текущей операции либо её
точный selector. На границах migration safety повторно проверяются фактические
owner, flow root, enrollment и targets. Это не перечитывает конфигурацию операции
и не расширяет права доступа.

???????????? native updater ?????????? ?????? effective PFConfig ? ?????????
device path ?? replacement. ????????? ????? ??????? child ???????? snapshot ??????
? accepted publication/manifest ? successor generation/epoch. Child maintenance
?????????? typed snapshot ? ?????????? pinned value ??? ?????????? ?????? live
configuration ? ???? ??????????. ????? ?? ????????? project/file/infra permissions.
