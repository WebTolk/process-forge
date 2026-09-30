# Project Flow Root

ProcessForge uses `.pf/` as the canonical project flow **state** root. New and
explicitly migrated projects also have root `AGENTS.md`, containing the full
minimum startup contract K for the selected client's instruction loader.
It is not a pointer to START and is not root-layout process state.

```text
project/
  AGENTS.md                    # minimum contract K + preserved user text
  .pf/
    AGENTS.md                  # same K + extended instructions
    agent-entry.json           # public contract/projection identity
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
      hooks/
      chat/
      queue/
```

START is no longer needed or automatically created. Existing START files remain
untouched; their absence does not affect readiness, doctor or repair.

Legacy projects without root entry use `.pf/AGENTS.md` explicitly until a
reviewed [entry migration](agent-entry.md) is applied. `legacy_or_unmigrated`
is an entry status, separate from snapshot freshness and project completeness.
A read-only check or startup prompt does not migrate the project.

## Public Files

Commit root `AGENTS.md`, `.pf/AGENTS.md`, `.pf/agent-entry.json`,
`.pf/process-forge.yaml`, `.pf/hooks.yaml`, context snapshots and reviewed flow
artifacts when the repository intentionally dogfoods ProcessForge. Preserve
user text outside managed sections; do not put secrets or local absolute paths
in these files. Existing customized entry text may require reconciliation.

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

Commands must not create root-layout flow state. If `.pf/process-forge.yaml`
is missing, use the explicit project onboarding path:

```text
pf project-onboard --project-root <project-root> --workplace <workplace-root> --type <project-type> --apply
```

`init-project` remains a compatibility command name. Root K being present and
within its 4096-byte internal ceiling does not prove client delivery or fit
within the client's aggregate instruction budget. See the
[entry support policy](agent-entry.md#compatibility-and-support-policy).
