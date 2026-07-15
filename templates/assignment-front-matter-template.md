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
hooks:
  tracking: detailed
  chat_capture: enabled
  emit_on_complete: true
  notify_wtaicc: outbox
chat_capture:
  enabled: false
  include_content: false
  max_message_chars: 20000
  redact_patterns:
    - secret_like
    - api_key_like
    - password_like
  allow_private_paths: false
  send_to_outbox: true
---

# Assignment: Example

Human-readable task description.
