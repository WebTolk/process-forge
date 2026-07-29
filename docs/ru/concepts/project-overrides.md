# Проектные отклонения

Project overrides - это project-local уточнения workspace resources. Они живут
в `.pf`, обычно в `.pf/project-overrides.yaml`, и могут ссылаться на локальные
override files.

Поддерживаемые modes: `overlay`, `extension`, `replace`, `parameterize`,
`disable`, `fork`. MVP resolver записывает applied overrides, применяет
`disable` к активируемым ресурсам и считает effective fingerprint из base hash,
override hash и merge mode.

Project overrides не изменяют workspace resources. Один проект может отключить
или параметризовать tool, template, MCP provider, knowledge package или
specialization, а другой проект в том же workspace останется без этого
отклонения.

Snapshot записывает applied overrides и fingerprints. Capsule получает только
summary активированных ресурсов и project overrides, а не полный raw content
knowledge или override files.
