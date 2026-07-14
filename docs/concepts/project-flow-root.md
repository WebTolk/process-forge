# Project Flow Root

New ProcessForge projects use `.pf/` as the default project flow root.

```text
project/
  .pf/
    AGENTS.md
    process-forge.yaml
    process-forge.local.yaml
    contexts/
    processes/
    packages/
    templates/
    assignments/
    artifacts/
    logs/
    handoffs/
    reviews/
    adr/
    schemas/
    runtime/
```

Root `AGENTS.md` is not created by default for a project. A root shim can be a
future opt-in, but it is not the default install layout.

## Public Files

Commit `.pf/AGENTS.md`, `.pf/process-forge.yaml`, `.pf/contexts/project-context.snapshot.*`,
and reviewed project flow artifacts.

## Private Files

Ignore:

```gitignore
.pf/process-forge.local.yaml
.pf/runtime/
.pf/private-notes/
.pf/cache/
```

Legacy root-layout projects are still supported. Migration to `.pf/` must be
planned and reviewed before moving existing evidence.
