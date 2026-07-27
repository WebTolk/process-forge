# Process Authoring

Process authoring помогает создать process definition через answers и draft,
а не через ручное написание YAML первым шагом.

Внутри подключенного проекта:

```bash
python .pf/runtime/bin/pf.py process-authoring-start --project-root . --id <process-id> --title "<title>" --scope project --kind operational --apply
python .pf/runtime/bin/pf.py process-authoring-review --project-root . --id <process-id>
python .pf/runtime/bin/pf.py process-authoring-apply --project-root . --id <process-id> --apply
python .pf/runtime/bin/pf.py process-doctor --project-root . --process <process-id>
```

После apply процесс можно использовать в `run-create`. Review должен проверить
stages, roles, artifacts, gates, required resources и run model.

## Transitions И Agents

Answers должны сначала выбрать `execution_mode`, а уже потом задавать advanced
role questions:

- `single_agent`
- `single_agent_with_subagents`
- `orchestrated_agents`
- `process_factory`

Для `single_agent` спрашивайте только primary-agent artifacts, mandatory gates,
CLI checks, ledger check-in/check-out и operator approval. Не задавайте вопросы
про Director, Supervisor, routes, leases или external workers, если пользователь
не выбрал режим, где эти механики нужны.

Answers могут включать `process_transitions`, `agent_requirements`,
`responsibility_boundaries`, `execution_mode_questions` и `subagent_policy`.
Эти поля фиксируют, может ли process передавать работу в
другие процессы, какие target processes и handoff modes разрешены, какие input
artifacts и expected output artifacts переходят через границу процесса, какая
receiving role или capability нужна, что делать при offline agent, нужна ли
continuation capsule, кто владеет run после handoff и может ли shell worker
вызывать subagents.

`responsibility_boundaries` фиксирует, кто координирует процесс, кто проверяет
runtime execution, кто выполняет assigned work и какие CLI checks заменяют
дорогое рассуждение в контексте агента. Используйте это поле, чтобы явно
развести обязанности Director/Ledger/Inspector/Worker: Director координирует
routes, leases, handoffs и continuations; Execution Inspector проверяет task
runtime status, heartbeat, exit, required outputs и expected reports; Worker
выполняет capsule task.

## Coordination Requirements

Process authoring должен фиксировать, как процесс ведёт себя в simple и
organized project mode:

```yaml
coordination_requirements:
  mode: simple_allowed # simple_allowed | organized_required | organized_optional
  director_inbox:
    required: false
    optional: true
  error_workflow:
    mode: none
error_handling:
  enabled: false
  mode: none
  fallback_if_no_director: needs_operator
```

`organized_required` не проходит `process-doctor` в effective simple project
без явного override. `simple_allowed` не должен требовать Director inbox.
`organized_optional` адаптируется к effective mode проекта.
