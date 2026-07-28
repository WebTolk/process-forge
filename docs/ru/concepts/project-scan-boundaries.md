# Границы сканирования проекта

ProcessForge считает distribution, workplace, knowledge roots, runtime и cache
поддерживающими ресурсами, а не обычным исходным кодом проекта.

Широкий meta-project может физически содержать:

```text
agents/
  processforge/
  docs/
  projects/
  snippets/
```

Если `agents/` подключён как `agent-workspace`, `brownfield-workspace` или
`meta-workspace`, scan проекта исключает `processforge/`, `docs/`, workplace
registries, runtime state и package caches по роли пути.

Knowledge roots остаются внешними ресурсами. Они доступны для context
resolution, но не становятся project source, если проект явно не включил их
будущей политикой.

Сам репозиторий ProcessForge считается проектом только с явным типом
`processforge-development` или `processforge-core-development`.
