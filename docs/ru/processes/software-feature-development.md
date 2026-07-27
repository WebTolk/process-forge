# Software Feature Development

`software-feature-development` - нейтральный lifecycle-процесс для разработки
ПО. Он ведёт задачу через `orchestration`, `intake-scope`, `investigation`,
`domain-modeling`, `architecture-plan`, `implementation`, `code-assurance`,
`release-delivery` и `evolve`.

`release-delivery` и `evolve` встроены в процесс, но могут быть условными. Для
маленькой локальной задачи агент должен записать `not_applicable` с причиной и
evidence, а не пропустить stage молча.

Delivery/build/package/install - это operation profile, а не отдельный PF
process. Платформенные команды должны жить в platform/project profile:

```yaml
process_id: software-feature-development
execution_profile:
  delivery_profile: project.default_delivery
```

Не добавляйте public core process вида `joomla-plugin-delivery`. Legacy artifact
`instruction-update-proposal` заменён на PF-neutral `instruction-update-proposal`.

В `evolve` этого процесса target set ограничен `knowledge_package`,
`delivery_profile`, `process_definition`, `project_rule` и `platform_contract`.
Build/release commands идут в delivery profile, process-flow findings - в
process definition, project-only constraints остаются project rules, а platform
constraints требуют явного applicability. Child-platform findings не
продвигаются в parent-platform rules без reviewed evidence.
