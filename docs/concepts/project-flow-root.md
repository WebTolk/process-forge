# Project Flow Root

ProcessForge projects use `.pf/` as the canonical project flow root.

```text
project/
  .pf/
    AGENTS.md
    process-forge.yaml
    process-forge.local.yaml
    hooks.yaml
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
      cache/
      sessions/
      telemetry/
      events/
        events.ndjson
      hooks/
        outbox/
        results/
      chat/
        transcripts/
      queue/
```

Root `AGENTS.md` is not created by default for a project. A root shim can be a
future opt-in, but it is not the default install layout.

## Public Files

Commit `.pf/AGENTS.md`, `.pf/process-forge.yaml`, `.pf/hooks.yaml`,
`.pf/contexts/project-context.snapshot.*`, and reviewed project flow artifacts
when the repository intentionally dogfoods ProcessForge.

Product distribution files such as `docs/`, `schemas/`, `tools/`, `processes/`,
`packages/`, `templates/`, and `examples/` may remain at repository root.

## Private Files

Ignore:

```gitignore
.pf/process-forge.local.yaml
.pf/runtime/
.pf/private-notes/
.pf/cache/
```

Commands must not create root-layout flow state. If `.pf/process-forge.yaml` is
missing, they should tell the operator to run `project-onboard --project-root
<project-root> --workplace <workplace-root> --type <project-type> --apply`.
`init-project` is a compatibility command name.
