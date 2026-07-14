# ProcessForge `.pf` Layout Migration Proposal

## Status

draft

## Objective

Move the ProcessForge product repository from legacy root flow layout to the new
`.pf/` project flow root without losing historical evidence, reviews, logs,
handoffs, or context artifacts.

## Current State

The product repository currently keeps flow files at the root:

```text
process-forge.yaml
contexts/
assignments/
artifacts/
logs/
reviews/
handoffs/
adr/
runtime/
```

The new implementation supports this layout as legacy. New target projects
created by `init-project` use `.pf/` by default.

## Proposed Stages

1. Keep root layout active while `.pf` support is tested in temporary projects.
2. Freeze a reviewed inventory of root flow files and protected evidence.
3. Create a copy-only `.pf/` migration branch or workspace state.
4. Move public flow files into `.pf/` and keep product source files at root.
5. Keep private runtime payload ignored and out of public artifacts.
6. Regenerate project context snapshot under `.pf/contexts/`.
7. Run schema validation, public cleanliness, context doctor, and session smoke.
8. Request review before deleting or archiving root legacy flow files.

## Do Not Move Without Review

- historical `contexts/*.ecp.yaml`
- `logs/*.md`
- `handoffs/*.md`
- `reviews/*.md`
- ADRs
- assignment evidence used by open handoffs

## Recommendation

Keep this task as Stage 1 support only. Approve migration separately after a
file inventory and review confirm which legacy artifacts remain active evidence.
