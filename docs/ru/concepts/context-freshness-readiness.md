# Freshness и execution readiness

Project context freshness отвечает за то, соответствует ли текущий resolved
snapshot каноническим входам проекта: manifest, registries, platform,
specialization, process, resource fingerprints и pinned resource instances.

Execution readiness отвечает за другое: может ли текущий агент выполнить
текущее действие процесса с доступными runtime capabilities.

Эти состояния разделены:

```yaml
readiness:
  context:
    status: fresh
  resources:
    status: fresh
  execution:
    status: blocked
    missing_capabilities:
      - capability: filesystem.write
        required_by: project.required_capabilities
```

Missing execution capability сам по себе не делает корректно resolved resources
stale. Например, Joomla knowledge resources могут быть fresh, а
`filesystem.write` отсутствовать. В этом случае:

```text
pf.session_context -> работает и показывает execution blocker
pf.search -> работает по авторизованным fresh resources
pf.resolve -> работает по resolved resources
write-dependent action -> blocked
```

`pf.search` по-прежнему fail-closed для stale resources, поврежденного snapshot,
чужого project binding или stale/degraded search index. Разделение readiness не
является bypass для resource authorization.
