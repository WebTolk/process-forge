# Порядок инициализации

Используйте этот порядок для новой установки ProcessForge, workplace и проекта:

1. Install ProcessForge distribution.
2. Verify ProcessForge itself.
3. Для human-led настройки по умолчанию запустить guided workplace setup; direct
   workplace-init использовать только для явно автоматического пути.
4. Configure path constants and roots.
5. Configure knowledge roots, especially local documentation roots.
6. Register tools and MCP servers.
7. Create/import knowledge packages.
8. Create reusable templates.
9. Create platform contracts.
10. Onboard project.
11. Create run/task workflow.
12. Create custom processes as needed.

## Почему platform contracts создаются позже

Platform contract не является первичным ресурсом. Это композиция поверх уже
существующих packages, templates, tools, MCP servers, processes, coding
standards и capabilities.

Не начинайте с platform contract, если его обязательные packages, templates или
tools ещё не созданы. Сначала создайте или зарегистрируйте зависимости, затем
создавайте platform contract.

Base languages и web technologies относятся к этим dependencies. Моделируйте их
как knowledge packages и capabilities, затем подключайте из platform contracts,
которым они нужны.

Тяжёлые локальные документации и исходники не записываются в public package
manifests. Ссылайтесь на них через workplace knowledge roots и package
resources с `path_ref`.

## Agent environments

Не копируйте весь репозиторий ProcessForge в `.codex`, `.claude`, `.agents` или
похожие папки конфигурации агентов.

Установите ProcessForge один раз как инструмент, инициализируйте workplace и
добавьте короткую инструкцию в конфигурацию агента: где установлен ProcessForge
и что проектные инструкции находятся в `.pf/START_AGENT_HERE.md`.
