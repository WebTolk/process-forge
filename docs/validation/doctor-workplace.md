# Doctor Workplace

Doctor Workplace validates a workplace root.

## Command

```bash
python bin/pf.py doctor-workplace --root <workplace-root>
```

`knowledge_roots.local-docs` is reported as `PASS` when configured. If it is
missing or empty, the doctor reports:

```text
WARN: knowledge_roots.local-docs missing or empty
Fix: add local-docs pointing to your documentation root
```

## Checks

- `workplace.yaml` exists.
- Required registry files exist.
- Required directories exist.
- Registry files are readable.
- Secret-like values are not stored.
- Required capabilities have providers when declared.
- Optional missing MCP providers are warnings, not failures.

## Result Format

```text
PASS: workplace.yaml found
WARN: optional MCP browser is not configured
FAIL: required capability repository.symbol_analysis has no provider
```

The command exits with a non-zero code when any `FAIL` result exists.
