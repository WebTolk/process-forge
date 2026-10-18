# R01 integration report

R01 is resolved as a contract-correction, not an indexer change. The shared
SQLite corpus is Workplace-owned and contains only registered Workplace
resources. Project-local generated profile data stays in the project context:
it is selected and resolvable, but a fresh new project may have no shared search
documents.

The user-like Garage smoke now proves that exact sequence: Garage context,
fresh empty search, project-profile resolution, then governed work start. The
Garage Core document explains how to register a reusable resource when shared
search is wanted. Focused Garage/search checks, checksum generation and scoped
diff validation passed.

The only shell worker was cancelled after an overlong diagnostic run without a
report. Its failure is preserved and did not contribute acceptance evidence.
No product authorization, index, registry, Runtime or installed-Core behavior
changed.
