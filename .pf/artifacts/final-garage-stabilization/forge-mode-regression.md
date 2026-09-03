# Forge Mode Regression

Date: 2026-08-24
Result: pass_with_conditions

Implemented invariant:

```text
Session enriches Garage; session does not promote Garage to Forge.
```

Evidence:

```text
python tools/smoke_garage_mode_not_promoted_by_session.py
PASS: bound session enriches Garage without promoting mode
```

The smoke verifies:

- simple project without session -> `mode: garage`;
- simple project with bound session -> `mode: garage`, `session.status: bound`;
- organized/Director-required snapshot -> `mode: forge`;
- missing required Forge infrastructure -> diagnostic
  `forge_runtime_required_but_unavailable`.

Condition:

Hosted Codex MCP visibility remains separate from local stdio MCP proof.
