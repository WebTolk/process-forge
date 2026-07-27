# Update Sites

Update site - это контракт ProcessForge для поиска новых версий установленных сущностей. Он остаётся file-first: без демона, базы данных, web UI и обязательной сети.

Основное поле адреса - `manifest_url`. Старое `url` принимается как legacy alias и сопровождается migration warning. `changelog_url` должен указываться для публичных обновлений пакетов, шаблонов, инструментов, процессов и knowledge-ресурсов, если меняется поведение.

В MVP реально покрыты smoke-тестами:

| Provider | Статус | Возможности |
| --- | --- | --- |
| `processforge_json_file` | implemented | локальный manifest и локальный artifact |
| `processforge_json` | implemented | HTTP/HTTPS manifest и artifact с timeout |
| `generic_http_directory`, `github_releases`, `gitlab_releases`, `gitverse_releases`, `tuf_repository` | planned | имя в контракте, без заявления о рабочей реализации |

Поддерживаются subject types: `processforge_distribution`, `workplace`, `process_package`, `knowledge_package`, `template_package`, `tool_package`, `tool_definition`, `platform_contract`, `mcp_definition`, `process_definition`, `reusable_template`, `knowledge_resource`.

`project_pf` не является обычным downloadable update subject. Для него используется assessment/migration path.
