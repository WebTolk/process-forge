# Public And Private Configuration

ProcessForge separates portable project configuration from local machine
configuration.

## Public Files

Public files can be committed.

Examples for `.pf` projects:

```text
.pf/AGENTS.md
.pf/process-forge.yaml
.pf/hooks.yaml
.pf/contexts/project-context.snapshot.yaml
.pf/contexts/project-context.snapshot.md
.pf/assignments/**
.pf/artifacts/**
.pf/reviews/**
.pf/handoffs/**
.pf/logs/**
.pf/adr/**
```

Product distribution files such as root `docs/`, `schemas/`, `tools/`,
`processes/`, `packages/`, `templates/`, and `examples/` are also public product
files.

Public files must not contain local absolute paths, secret values, private
machine names, or local-only knowledge roots.

## Private Files

Private files stay local.

Examples:

```text
.pf/process-forge.local.yaml
.pf/runtime/**
.pf/cache/**
.pf/private-notes/**
.secrets/**
```

## Required Ignore Policy

Project Init adds these entries to project `.gitignore`:

```gitignore
.pf/process-forge.local.yaml
.pf/runtime/
.pf/private-notes/
.pf/cache/
```

If a local runner is used later, queue and agent runtime state remain private.
