# Public And Private Configuration

ProcessForge separates portable project configuration from local machine configuration.

## Public Files

Public files can be committed.

Examples:

```text
AGENTS.md
process-forge.yaml
docs/**
schemas/**
processes/**
packages/**
templates/**
assignments/**
artifacts/**
reviews/**
handoffs/**
```

Public files must not contain local absolute paths, secret values, private machine names, or local-only knowledge roots.

## Private Files

Private files stay local.

Examples:

```text
process-forge.local.yaml
cache/**
.secrets/**
```

Runtime files may be private in generated projects. In the ProcessForge product repository, `runtime/` is kept as a draft protocol directory.

## Required Ignore Policy

Project Init adds these entries to project `.gitignore`:

```gitignore
process-forge.local.yaml
runtime/
cache/
.secrets/
*.tmp
*.bak
```

If a local runner is used later, queue and agent runtime state remain private.
