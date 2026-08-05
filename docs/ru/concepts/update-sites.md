# Сервера обновлений

Сервер обновлений - это источник, по которому ProcessForge узнаёт, есть ли новая
версия установленной сущности: ядра ProcessForge, рабочего места, пакета
процессов, знаний, шаблонов, инструментов, платформенного контракта или MCP.
Контракт остаётся файловым: для проверки не нужен демон, база данных или
обязательный внешний веб-сервис. В тестах сервером обновлений может быть
локальный файл.

Обновляемая сущность объявляет один или несколько записей `update_sites`:

```yaml
update_sites:
  - id: vendor-main
    enabled: true
    provider: processforge_json_file
    manifest_url: "file:///mirror/acme-processes.json"
    changelog_url: "file:///mirror/acme-processes-changelog.md"
    channel: stable
    priority: 10
    trust:
      require_https: false
      require_sha256: true
      allow_unsigned: true
      signature_required: false
    policy:
      check_interval_hours: 24
      auto_check: true
      auto_stage: false
      auto_apply: false
      notify_operator: true
      notify_director_inbox: true
```

Главное поле адреса - `manifest_url`. Старое поле `url` всё ещё принимается как
устаревший вариант, но валидатор выдаёт предупреждение о миграции.
`changelog_url` нужно указывать для публичных обновлений пакетов, шаблонов,
инструментов, процессов и ресурсов знаний, если обновление меняет поведение.

Реально проверенные provider-ы:

| Provider | Статус | Что умеет |
| --- | --- | --- |
| `processforge_json_file` | implemented | читает локальный манифест и копирует локальный артефакт |
| `processforge_json` | implemented | читает HTTP/HTTPS-манифест и скачивает артефакт с таймаутом |
| `generic_http_directory`, `github_releases`, `gitlab_releases`, `gitverse_releases`, `tuf_repository` | planned | имя есть в контракте, рабочая реализация не заявлена |

Публичные smoke-тесты используют локальные `file:///` манифесты и артефакты,
чтобы проверка была воспроизводимой.

Поддерживаемые типы установленных сущностей: `processforge_distribution`,
`workplace`, `process_package`, `knowledge_package`, `template_package`,
`tool_package`, `tool_definition`, `platform_contract`, `mcp_definition`,
`process_definition`, `reusable_template`, `knowledge_resource`.

`project_pf` не является обычным скачиваемым обновлением. Для проектной `.pf`
используется отдельный путь оценки и миграции: ProcessForge пишет отчёт, а
изменения в проекте выполняются явно после решения оператора.

## Связь с Evolve

Evolve не обходит сервера обновлений. После проверки и отбора накопленных
улучшений knowledge hub выпускает версию пакета и локальный манифест обновления.
Рабочее место затем использует обычные команды `update candidates refresh`,
`update stage`, `update verify` и `update apply`.

Черновые кандидаты и сгенерированные learning bundles не попадают в публичный
архив. Распространяются только проверенные релизы пакетов и их манифесты
обновления.
