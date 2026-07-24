# Context Capsule

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

## Worker Contract

Worker читает только required sources, если assignment явно не расширяет scope.
Если `worker_may_rebuild_context` равен `false`, worker не перестраивает полный
project context.
