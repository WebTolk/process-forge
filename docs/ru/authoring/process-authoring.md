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

Answers могут включать `process_transitions`, `agent_requirements` и
`subagent_policy`. Эти поля фиксируют, может ли процесс передавать работу в
другие процессы, какие target processes и handoff modes разрешены, какие input
artifacts и expected output artifacts переходят через границу процесса, какая
receiving role или capability нужна, что делать при offline agent, нужна ли
continuation capsule, кто владеет run после handoff и может ли shell worker
вызывать subagents.
