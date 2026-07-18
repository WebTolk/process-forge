# Platform Contracts

Platform contract связывает тип проекта с рекомендуемыми ресурсами
ProcessForge: knowledge packages, templates, tools, MCP servers и default
processes.

Контракт помогает `project-onboard` подобрать начальные правила для проекта по
project type hints.

Создание:

```bash
python bin/pf.py platform-create --workplace <workplace-path> --id <platform-id> --title "<title>" --apply
python bin/pf.py platform-contract-doctor --workplace <workplace-path> --platform <platform-id>
```

Контракт должен ссылаться на ресурсы по id, а не копировать их.
