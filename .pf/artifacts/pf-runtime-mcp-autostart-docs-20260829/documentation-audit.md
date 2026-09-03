# Аудит документации Runtime и MCP

## Статус

Аудит не выполнен: предоставленного scope недостаточно для достоверной инвентаризации документационных утверждений и исполняемого lifecycle-поведения Runtime/MCP.

## Причина блокировки

В assignment указано:

- `worker_may_rebuild_context: false`
- `allowed_read_files: []`
- `workspace_access.knowledge_resources: 0`
- `workspace_access.tools: 0`
- `workspace_access.mcp: 0`
- `workspace_access_file` не предоставляет дополнительных ресурсов в капсуле
- задача требует анализа документации и исполняемого поведения, но чтение исходников, документации и обязательных источников фактически не разрешено

При этом цель задания требует:

> Inventory documentation claims and executable lifecycle behavior for Runtime and MCP, identify contradictions and requirements for Windows autostart.

Для этого необходимо читать как минимум документационные файлы Runtime/MCP и соответствующий код lifecycle/autostart. Эти файлы не входят в `allowed_read_files`.

## Что можно подтвердить по капсуле

Проект классифицирован как `software.python`.

Задание имеет режим:

- `kind: docs_only`
- `code_changes_allowed: false`
- `artifact_changes_allowed: true`
- `requires_review: true`

Единственный разрешенный файл вывода:

- `.pf/artifacts/pf-runtime-mcp-autostart-docs-20260829/documentation-audit.md`

## Недоступные для проверки области

Не удалось проверить:

- какие claims уже есть в документации Runtime
- какие claims уже есть в документации MCP
- как фактически реализован lifecycle Runtime
- как фактически реализован lifecycle MCP
- есть ли автозапуск MCP/Runtime на Windows
- какие требования к Windows autostart уже задокументированы
- какие противоречия есть между документацией и кодом
- какие требования нужно добавить или исправить

## Требуемое расширение scope

Для выполнения аудита нужно разрешить чтение:

- `.pf/contexts/project-context.snapshot.yaml`
- `.pf/assignments/pf-runtime-mcp-docs-audit-20260829.yaml`
- документации Runtime/MCP
- исходников Runtime/MCP lifecycle
- исходников или конфигурации Windows autostart, если они существуют
- README/architecture/design docs, где описаны Runtime, MCP или autostart

## Итог

Работа остановлена по правилу assignment: scope недостаточен для выполнения задачи без выхода за `allowed_read_files`.