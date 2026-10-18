# Context capsule

Новые капсулы в исходниках содержат [единый контракт выполнения](work-context.md):
неизменное назначение, явные права и идентичность обязательных входных файлов.
Старые капсулы сохраняются; `--force` не заменяет закреплённый контекст.

Context capsule - это небольшой launch package для worker-agent. Он ссылается
на Execution Context Package и несёт минимальную policy, нужную для bounded
assignment.

В [multi-agent orchestration](multi-agent-orchestration.md) каждый worker launch
prompt указывает на одну assignment capsule. Capsule ограничивает worker его
assignment, required sources, allowed scopes, forbidden files, required outputs
и context rebuild policy.

## Contents

Capsule включает:

- capsule id
- referenced Execution Context Package
- assignment path
- required sources
- allowed files
- forbidden files
- `worker_may_rebuild_context`
- freshness status

## Worker contract

Worker читает только required sources, если assignment явно не расширяет scope.
Если `worker_may_rebuild_context` равен `false`, worker не перестраивает полный
project context.
