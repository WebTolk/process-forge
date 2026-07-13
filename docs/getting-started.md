# Getting Started

ProcessForge starts with files, not services.

## Start a Project

1. Copy the ProcessForge directory into the project root.
2. Review `process-forge.yaml`.
3. Adjust project id, name, packages, and process references.
4. Create an assignment from `templates/assignment-template.md`.
5. Create an Execution Context Package from `templates/execution-context-package-template.yaml`.
6. Work inside the assignment boundary.
7. Record outputs in artifacts, reviews, handoffs, and logs.

## Minimal Run

```text
assignment -> execution context -> work -> artifact -> review -> handoff -> log
```

## Validation

Run:

```bash
python tools/validate-process-forge-schemas.py
python tools/validate-process-forge-checksums.py
python tools/validate-public-cleanliness.py
```
