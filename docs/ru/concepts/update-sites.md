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

`manifest_url` указывает на манифест обновления. `changelog_url` указывает на
человекочитаемый список изменений. Манифест может быть локальным файлом, как в
примере выше, или удалённым HTTP(S)-адресом. ProcessForge выбирает способ
чтения по самому URL; оператору не нужно объявлять тип источника.

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
улучшений knowledge hub выпускает версию пакета и локальный манифест
обновления. Рабочее место затем использует обычные команды
`update candidates refresh`, `update stage`, `update verify` и `update apply`.

Черновые кандидаты и сгенерированные learning bundles не попадают в публичный
архив. Распространяются только проверенные релизы пакетов и их манифесты
обновления.
