# Workplace vs project

Workplace и project — разные слои ProcessForge.

Workplace хранит машинные и общие ресурсы:

- реестры;
- повторно используемые шаблоны;
- пакеты знаний;
- platform contracts;
- общие настройки по умолчанию.

Project хранит проектный рабочий слой:

- `.pf/START_AGENT_HERE.md`;
- `.pf/process-forge.yaml`;
- process definitions;
- runs, tasks и iterations;
- артефакты, проверки и handoffs;
- project context snapshot.

Не копируйте весь ProcessForge в проект или в папки конфигурации агентов. Установите
ProcessForge как инструмент, создайте workplace и подключайте проекты через
`project-onboard`.

Папки конфигурации агентов вроде `.codex`, `.claude` и `.agents` должны
содержать только короткую инструкцию: где установлен ProcessForge и что
проектные инструкции находятся в `.pf/START_AGENT_HERE.md`.

Workplace хранит машинные пакеты знаний, повторно используемые шаблоны,
инструменты, MCP servers, platform contracts и корни вроде
`knowledge_roots.local-docs`. Project получает папку `.pf/` через
`project-onboard`; он не получает копию репозитория ProcessForge, тяжёлую
документацию или деревья исходного кода.
