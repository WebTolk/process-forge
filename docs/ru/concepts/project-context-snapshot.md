# Project Context Snapshot

Project context snapshot - вычисленная operational map проекта ProcessForge. Он
создается во время project init или project-context-refresh и читается в начале
сессии до широких scans по packages или templates.

Основные пути:

```text
.pf/contexts/project-context.snapshot.yaml
.pf/contexts/project-context.snapshot.md
.pf/contexts/project-context.snapshots/<snapshot-id>.yaml
.pf/runtime/cache/workplace-context.snapshot.yaml
```

Snapshot строится из структурированных источников:

- workplace и project manifests
- process definitions
- package definitions
- tool, MCP, template и specialization registries
- selected specialization definitions и platform bindings
- project overrides
- platform contracts
- source fingerprints
- observed `project_classification` со status, classifier/rule IDs, project
  types, platforms и tags

Snapshot записывает selected platform, platform stack, selected
specializations, active resource profile, execution route, required
capabilities, provided capabilities, capability resolution, applied project
overrides, effective fingerprints и conflicts. Capabilities остаются opaque IDs;
snapshot не разворачивает полный knowledge content.

Snapshot также записывает `resolved_parameters` и `parameter_resolution`.
Параметры собираются только из структурированных источников: workplace
`parameters`, `registries/parameters.yaml`, активных platform/specialization
sources, project manifest, private `overrides.parameters`, `.pf/parameters.yaml`,
`.pf/parameters.local.yaml`, process/stage/task/assignment `parameters` при их
активации. `AGENTS.md` и другие Markdown-инструкции не являются машинными
источниками параметров.

Merge параметров нейтрален к предметной области: maps сливаются рекурсивно,
scalars заменяются более конкретным слоем, списки объектов с `id` сливаются по
`id`, списки без `id` заменяются целиком, `null` удаляет ключ map, а `_delete`
или `__delete__` удаляет элемент списка по `id`.

`capability_resolution` содержит satisfied и unsatisfied requirements. PF core
не удовлетворяет user process capabilities по умолчанию. Если active resource
profile не предоставляет required capability, snapshot фиксирует ее как
`unsatisfied`, а context получает ресурсный conflict/status.

Freshness учитывает specialization definitions, specialization registry,
project specialization overrides, `project-overrides.yaml`, active
tool/MCP/template registries, active project classifiers и результат их
применения, process definition и selected platform contracts.
Existing run/capsule остается pinned; новая сессия должна refresh или сообщить
stale/fresh_with_updates согласно policy.

Runtime workplace snapshot может содержать local availability state для tools и
MCP. Он лежит в `.pf/runtime/cache/` и остается private.
