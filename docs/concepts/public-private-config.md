# Public And Private Configuration

ProcessForge separates portable project configuration from local machine
configuration.

## Public Files

Public files can be committed.

Examples for new `.pf` projects:

```text
.pf/AGENTS.md
.pf/process-forge.yaml
.pf/contexts/project-context.snapshot.yaml
.pf/contexts/project-context.snapshot.md
.pf/schemas/**
.pf/processes/**
.pf/packages/**
.pf/templates/**
.pf/assignments/**
.pf/artifacts/**
.pf/reviews/**
.pf/handoffs/**
.pf/logs/**
.pf/adr/**
```

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

Legacy root-layout projects may still use root-level `process-forge.local.yaml`
and `runtime/` until migration is reviewed.

## Required Ignore Policy

Project Init adds these entries to project `.gitignore`:

```gitignore
.pf/process-forge.local.yaml
.pf/runtime/
.pf/private-notes/
.pf/cache/
```

If a local runner is used later, queue and agent runtime state remain private.
