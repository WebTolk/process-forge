# Garage Session-Enhanced Acceptance

Date: 2026-08-24
Status: pass

Evidence:

```text
python tools/smoke_garage_session_enhanced.py
PASS: Garage session-aware mode preserves resource authorization

python tools/processforge.py release-test --root . --no-clean --only smoke_garage_session_enhanced
PASS smoke_garage_session_enhanced
```

Covered behavior:

- sessionless and session-aware `pf.search` return the same authorized resource;
- `pf.context` switches to `mode: forge` when a matching session id is supplied;
- resource authorization remains project-snapshot based.
