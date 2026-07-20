# Platform Inheritance

Platform contracts могут наследоваться от других platforms через `extends` и
требовать другие platforms через `requires.platforms`.

Platform inheritance - generic graph resolution поверх manifests. Ядро
ProcessForge не содержит domain branches для конкретных implementation,
documentation, content, operations или business platforms.

```yaml
extends:
  - id: platform.example-parent
    version: "^1.0"
    required: true

requires:
  platforms:
    - id: platform.example-parent
      version: "^1.0"
      required: true
```

Shorthand form для `extends` тоже принимается:

```yaml
extends:
  - platform.example-parent
```

Documentation и generated reports должны предпочитать full form.

## Semantics

`extends` означает inheritance. Parent platform добавляет packages, templates,
tools, capabilities, rules, processes, project type hints и coding standards в
resolved stack.

`requires.platforms` означает dependency. Platform не может быть valid, если
required platform недоступна. В MVP `extends` подразумевает required parent.

Base languages и web technologies не должны становиться parent platforms.
Моделируйте их как knowledge packages и capabilities. Platform contract может
включать такие packages напрямую, а child platform наследует их только если
parent platform manifest их добавляет.

## Merge Rules

ProcessForge сначала разрешает parent platforms, объединяет parent resources,
затем применяет child platform.

Эти collections merge by `id`: `knowledge_packages`, `templates`, `tools`,
`mcp_servers`, `capabilities`, `processes`, `project_type_hints` и
`coding_standards`.

Conflict rules:

- required parent плюс optional child остаётся required;
- optional parent плюс required child становится required;
- разные versions для одного package, tool или platform дают warning или
  failure в зависимости от required flag;
- duplicate ids deduped, warning появляется при различии metadata;
- remove и override rules находятся за пределами MVP.

`project-onboard` записывает deterministic `platform_stack` и включает
inherited knowledge packages в `knowledge_stack`.

Любая internal или external platform может использовать те же поля `extends`,
`requires.platforms`, `includes.*` и `detection` без Python changes. Например,
документация может описывать реальный stack Joomla -> JoomShopping, но этот
пример должен оставаться в docs/examples, а не в core seeds, templates, tests
или flow artifacts.
