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
---

# Assignment: Example
```

If front matter is missing, the assignment is human-readable only. It can guide
manual work, but it cannot produce an automated context capsule.

Use:

```bash
python tools/processforge.py assignment-capsule --project-root <project-root> --assignment <assignment-file>
```
