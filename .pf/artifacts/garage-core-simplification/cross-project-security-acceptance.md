# Cross-Project Security Acceptance

Date: 2026-08-24
Status: pass

Evidence:

```text
python tools/smoke_garage_cross_project_security.py
PASS: Garage resource authorization is snapshot-bound across projects

python tools/processforge.py release-test --root . --no-clean --only smoke_garage_cross_project_security
PASS smoke_garage_cross_project_security
```

Covered behavior:

- project A cannot search project B's resource text;
- project A receives `denied` when resolving project B's resource id;
- a session bound to project A cannot be combined with project B root.
