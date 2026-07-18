# Assignment Front Matter

Automated assignment execution uses YAML front matter or a separate assignment
YAML file as its machine-readable source. Markdown headings and prose are for
humans and agents, not for stable machine authority.

Example:

```markdown
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
---

# Assignment: Example
```

If front matter is missing, the assignment is human-readable only. It can guide
manual work, but it cannot produce an automated context capsule.

Use:

```bash
python bin/pf.py assignment-capsule --project-root <project-root> --assignment <assignment-file>
```

The generated capsule includes the snapshot checksum, scope, capabilities,
required outputs, telemetry path, and event correlation id.

Assignment hook options can request detailed tracking or chat capture, but they
cannot disable process-required events unless the process policy allows it. Chat
content remains metadata-only for outbox delivery unless `include_content` is
explicitly enabled.
