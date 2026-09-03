# Garage Sessionless Work Acceptance

Date: 2026-08-24
Result: pass

Expected:

```text
pf.context -> mode=garage
pf.search -> pass
pf.resolve -> pass
pf.work.start -> pass, session.status=absent
```

Evidence:

```text
python tools/smoke_garage_no_hooks_sessionless.py
PASS: Garage context/search/resolve work without hooks, session, or daemon

python tools/smoke_garage_work_start_sessionless.py
PASS: sessionless pf.work.start creates governed work
```

Covered:

- no Ledger session;
- no hook requirement;
- no daemon requirement;
- governed work can start from project-local `.pf` authority.
