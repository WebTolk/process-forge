# Platform Inheritance

Platform contracts can inherit from other platforms with `extends` and can require other platforms with `requires.platforms`.

Platform inheritance is generic graph resolution over manifests. ProcessForge
core does not contain domain branches for any specific implementation,
documentation, content, operations, or business platform.

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

The shorthand form is accepted for `extends`:

```yaml
extends:
  - platform.example-parent
```

Documentation and generated reports should prefer the full form.

## Semantics

`extends` means inheritance. A parent platform contributes packages, templates, tools, capabilities, rules, processes, project type hints, and coding standards to the resolved stack.

`requires.platforms` means dependency. The platform cannot be valid unless the required platform is available. For the MVP, `extends` implies a required parent.

A derived platform is never selected only because it repeats a project type
hint declared by its parent. Select it with a child-specific type hint, explicit
project input, classifier evidence, or a concrete detection rule declared by
that derived contract.

Base languages and web technologies should not become parent platforms. Model
them as knowledge packages and capabilities. A platform contract can include
those packages directly, and a child platform inherits them only when its parent
platform manifest contributes them.

## Merge Rules

ProcessForge resolves parent platforms first, merges parent resources, then applies the child platform.

These collections merge by `id`: `knowledge_packages`, `templates`, `tools`, `mcp_servers`, `capabilities`, `processes`, `project_type_hints`, and `coding_standards`.

Conflict rules:

- required parent plus optional child remains required;
- optional parent plus required child becomes required;
- different versions for the same package, tool, or platform produce a warning or failure depending on the required flag;
- duplicate ids are deduped, with a warning when metadata differs;
- remove and override rules are outside the MVP.

`project-onboard` writes a deterministic `platform_stack` and includes inherited knowledge packages in `knowledge_stack`.

Any internal or external platform can use the same `extends`,
`requires.platforms`, `includes.*`, and `detection` fields without Python
changes. For example, documentation can describe a real stack such as
Joomla -> JoomShopping, but that example must stay in docs/examples rather than
core seeds, templates, tests, or flow artifacts.

## Evolve Candidates

Evolve candidates do not inherit upward by default. A learning observed on a
child platform is recorded with `source_context.platform_stack` and
`applicability.inheritance.observed_on`; that evidence does not make the
candidate a parent-platform rule.

To affect a parent platform, the candidate must target the parent package or
contract explicitly, use `generalization.level: parent_platform_candidate` or a
reviewed parent rule level, and include a `promotion` block. Until promotion is
approved, package builds stage parent candidates in incoming learnings rather
than curated package notes.

Use `applicability.not_applies_to` and `conditions` when a child override makes
the rule unsafe for siblings. If the same run discovers both a child-specific
constraint and a broader parent-platform possibility, split them into separate
candidates.
