# Platform Contract Authoring

Platform contract описывает, какие capabilities, knowledge packages, templates,
tools, MCP servers и default processes нужны проектам определенного типа.

```bash
python bin/pf.py platform-create --workplace <workplace-path> --id <platform-id> --title "<title>" --apply
python bin/pf.py platform-contract-doctor --workplace <workplace-path> --platform <platform-id>
```

Platform contract не должен копировать пакеты знаний или шаблоны внутрь себя.
Он ссылается на них по id, чтобы ресурсы оставались переиспользуемыми.
