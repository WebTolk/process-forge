# Context Freshness

Project context freshness answers whether the current snapshot still represents
the project flow inputs.

A snapshot is stale when:

- `valid_until` has expired
- a source fingerprint changed
- a source was added or removed
- workplace or local config fingerprints changed
- selected package or process sources changed
- a required capability provider is missing

The check output separates freshness from health:

```text
STATUS: fresh | stale | missing
HEALTH: pass | warn | blocked
RESULT: pass | fail
```

`generated_at` alone is not part of source freshness. Regenerating a snapshot
without source changes must not make the previous snapshot stale by itself.

Use:

```bash
python bin/pf.py project-context-check --project-root <project-root>
```

Refresh with:

```bash
python bin/pf.py project-context-refresh --project-root <project-root>
```
