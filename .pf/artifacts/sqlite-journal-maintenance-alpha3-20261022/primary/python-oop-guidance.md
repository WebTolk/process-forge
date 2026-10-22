# PF-selected Python and OOP guidance for maintenance alpha3

Actually resolved through the exact Work: docs.python:root,
docs.python-practices:root and docs.python-peps:root. Read local typing.md
structural-subtyping discussion, dataclasses.md frozen/default-factory rules,
pathlib.md resolution/symlink distinctions, typing-guide.md navigation and PEP544
abstract/rationale. PEP544 is historical; current typing.py documentation is the
runtime/static interface reference. No external guide body is claimed from a link.

Use small responsibility-based services and constructor injection. A narrow
Protocol describes a real backup or scanner operation, not an Any-core facade.
Use composition for the different storage/validation policies; no DI container,
service locator, plugin loader or deep inheritance. Constructors remain cold.
Related errors/values stay with their owner; immutable receipts may use frozen
dataclasses and defensive immutable collections. Serialized operator reports
are plain JSON-compatible values with honest unavailable/unknown status.

Patterns applied: Repository via existing ProcessEventJournal/RawHookJournal and
SQLite helpers; Application Service for ordered maintenance; Strategy/ports for
backup/scanning dependencies; Adapter for CLI/legacy entrypoint; immutable Value
Object for receipts/signatures. Do not create a class per utility function.

Use actual explicit roots, binary source reads and preserved byte offsets.
Path.resolve/is_relative_to is containment handling, not authorization. Refuse
unexpected symlinks and unsafe manifest members; never interpret an imported
document as code or a source of grants. JSON rejects nonfinite numbers.

SQLite backup uses the existing backup API pattern already present in accounting
storage, rather than copying a live DB/WAL file. Validate backup and restore with
integrity_check, hashes, counts and meaningful failure tests. Report statements
must distinguish one-database snapshot consistency from a multi-database global
transaction; no such global snapshot is promised.

Shared registered PF tools: python-pytest, python-ruff, python-formatter,
python-mypy; coverage and Bandit are relevant to data maintenance. The primary
resolved python/toolchain.json through the workplace. Versions read: Python3.14.3,
pytest9.1.1, Ruff0.17.1, mypy2.4.0, coverage7.16.2, Bandit1.9.4. Follow project
configuration, PEP8/257 and meaningful Google-style docstrings. Lint/check does
not silently fix files; explicit formatting is separate. Quality dependencies
remain outside Core. Test behavior, corruption, identity, idempotency and effects,
not class counts or mirrored implementation. No new dependency is planned.

Architecture precedence: current migration-contract and clarification constrain
the older ADR/domain/direction. Shared Core code cannot call back to Main/Host.
Reuse existing owners and preserve old external CLI/MCP contracts; new commands
are an explicitly authorized maintenance feature, not a covert refactor change.
