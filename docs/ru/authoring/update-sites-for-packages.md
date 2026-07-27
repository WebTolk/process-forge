# Update Sites Для Пакетов

Process, knowledge, template, tool, platform, process definition и MCP manifests могут объявлять `update_sites`. Для публичного обновления, меняющего поведение, указывайте `manifest_url` и `changelog_url`.

Tool updates имеют отдельную policy. В MVP поддержан deterministic `replace_file`; `custom_command_requires_confirmation` не исполняется автоматически и требует отдельного явного решения оператора.

Локальные overrides хранятся в `<workplace>/registries/update-site-overrides.yaml`. Через них можно отключить subject, заменить `manifest_url`, сменить `channel`, закрепить `pin_version`, запретить major updates или оставить apply только ручным.
