# Project Flow Layer

The project flow layer describes how ProcessForge is used inside one project.

It answers:

```text
How should this project run repeatable work?
```

The default flow root is `.pf/`, and the default manifest is
`.pf/process-forge.yaml`. Legacy root-layout projects remain supported until a
reviewed migration moves their flow files.

## Responsibilities

- Reference the workplace layer.
- Select process definitions.
- Select knowledge packages.
- Select templates.
- Declare tool and MCP capability requirements.
- Store assignments, artifacts, contexts, logs, handoffs, reviews, and ADRs.
- Define project-specific overrides.
- Stay usable without a backend or mandatory runner.

## Manifest

The project manifest declares paths, process references, package references,
validation scripts, merge policy, ownership policy, runner mode, and
public/private metadata.
