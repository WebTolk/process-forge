# Workplace vs Project

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
