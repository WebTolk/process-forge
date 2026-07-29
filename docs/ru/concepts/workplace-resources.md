# Workplace Resources

Workplace resources - reusable assets, которые хранятся вне отдельных проектных
`.pf/` folders.

Основные resource groups:

- knowledge packages в authoritative package roots
- reusable templates в template roots
- platform contracts в platform contract roots
- registered tools и MCP providers
- явно зарегистрированные project classifiers
- optional capability registries и `provides_capabilities` declarations на
  active resources

Проекты выбирают resources через workplace registries и platform contracts.
Public project files хранят IDs, relative paths и snapshot summaries; они не
копируют private local paths или heavyweight resource payloads.

Реестры classifiers по умолчанию пусты. Необязательный package становится
активным только после явной регистрации его ресурсов оператором или
installation flow.

Capabilities являются workspace/project/package data. PF core не активирует
domain examples и не предоставляет software, web, media, legal или другие
domain capability IDs по умолчанию.

Authoring commands пишут events в `runtime/events/events.ndjson`, чтобы hooks и
reviews могли отслеживать lifecycle resources.
