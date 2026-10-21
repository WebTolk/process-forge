# Scope

## In Scope
- tools/pf_runtime/kimi_adapters.py
- tools/pf_runtime/kimi_hooks.py
- tools/pf_runtime/builtin_provider_adapters.py
- ruff check / format
- mypy (focused, with known import limitations)

## Out of Scope
- Full project mypy run (known existing issues in src/processforge_core)
- Architecture changes

## Acceptance
- [x] ruff check passes
- [x] ruff format passes
- [x] mypy focused run documented
