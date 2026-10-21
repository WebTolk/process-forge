# Architecture

## Audit architecture

```
QualityRunner (tools/python-qa/.venv)
  -> ruff check (style)
  -> ruff format (formatting)
  -> mypy (typing, focused)
  -> QualityReport (.pf/artifacts/kimi-audit-*/)
```

## Components
- Shared Python QA: ruff 0.17.1, mypy 2.4.0
- Target files: kimi_adapters.py, kimi_hooks.py, builtin_provider_adapters.py
- Reports: ruff JSON, mypy text, investigation-report.md
