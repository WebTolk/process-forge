# Decision Log

| Decision | Rationale |
|---|---|
| Fix unsorted imports manually | Ruff I001 has safe autofix, but manual edit is clearer. |
| Use ruff format for auto-fix | Consistent with project toolchain. |
| Add type annotation + assert for mypy | Minimal fix without changing runtime behavior. |
| Document known mypy limitations | Import path and dynamic Logger are pre-existing project issues. |
