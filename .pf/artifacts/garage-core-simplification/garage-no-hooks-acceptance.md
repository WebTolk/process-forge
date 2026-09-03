# Garage No-Hooks Acceptance

Date: 2026-08-24
Status: pass

Evidence:

```text
python tools/smoke_garage_no_hooks_sessionless.py
PASS: Garage context/search/resolve work without hooks, session, or daemon

python tools/processforge.py release-test --root . --no-clean --only smoke_garage_no_hooks_sessionless
PASS smoke_garage_no_hooks_sessionless
```

Covered behavior:

- no `.codex` hook dependency;
- no `--session` or `PF_MCP_SESSION_ID`;
- stdio MCP `pf.context`, `pf.search`, and `pf.resolve`;
- snapshot-authorized resource only.
