# Resource Management Review

## Reviewed Object

- command:
- package:
- resource/template/tool/mcp:

## Checks

- Proposal created before apply.
- Public project files contain no private absolute paths.
- Resource records use `path_ref`.
- Heavy resources use `load_policy`.
- Events were emitted.
- Package index validates.

## Result

pass_with_conditions

## Known Risks

- Healthchecks are metadata-only unless an explicit runner executes them.
- Documentation import is plan-only in MVP.
