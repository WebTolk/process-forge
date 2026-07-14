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

`generated_at` alone is not part of source freshness. Regenerating a snapshot
without source changes must not make the previous snapshot stale by itself.

Use:

```bash
python tools/processforge.py project-context-check --project-root <project-root>
```

Refresh with:

```bash
python tools/processforge.py project-context-refresh --project-root <project-root>
```
