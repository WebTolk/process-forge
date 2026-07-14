---
schema_version: 1
id: example-assignment
status: ready
role: worker
process: software-feature-development
stage: implementation
required_capabilities:
  - repository.read
optional_capabilities:
  - repository.symbol_analysis
allowed_files:
  - .pf/artifacts/**
forbidden_files:
  - .pf/runtime/**
  - .pf/private-notes/**
required_outputs:
  - .pf/artifacts/example-report.md
---

# Assignment: Example

Human-readable task description.
