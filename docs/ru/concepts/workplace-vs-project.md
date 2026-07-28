# Workplace vs project

Workplace и project — разные слои ProcessForge.

Workplace хранит машинные и общие ресурсы:

- registries;
- reusable templates;
- knowledge packages;
- platform contracts;
- shared defaults.

Project хранит проектный flow:

- `.pf/START_AGENT_HERE.md`;
- `.pf/process-forge.yaml`;
- process definitions;
- runs, tasks и iterations;
- artifacts, reviews и handoffs;
- project context snapshot.

Не копируйте весь ProcessForge в проект или в agent config folders. Установите
ProcessForge как инструмент, создайте workplace и подключайте проекты через
`project-onboard`.

Agent configuration folders вроде `.codex`, `.claude` и `.agents` должны содержать только короткую инструкцию: где установлен ProcessForge и что project-specific instructions находятся в `.pf/START_AGENT_HERE.md`.

Workplace хранит machine-level knowledge packages, reusable templates, tools, MCP servers, platform contracts и roots вроде `knowledge_roots.local-docs`. Project получает `.pf/` папку через `project-onboard`; он не получает копию репозитория ProcessForge или тяжёлые documentation/source trees.
