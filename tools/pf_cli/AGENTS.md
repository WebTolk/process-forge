# CLI structure

Keep CLI implementation in shallow responsibility packages. Use lowercase
package names, `snake_case.py` modules and `CapWords` classes. Related classes
may share a module; a class does not require its own file. Keep `__init__.py`
minimal and import directly from the owning module.

- `application.py` owns one invocation: parsing, mode checks and dispatch.
- `parsers/` owns argument registration. Registrars receive explicit handlers
  and values, then a public `add_parser` callback. Preserve registration order,
  defaults, aliases, validators, help and parse errors. Allocate mutable defaults
  during registration, separately for each parser build.
- `commands/` holds extracted command adapters. Give each independent executable
  handler a concrete class with `execute(args)`. Group related commands by
  responsibility; do not clone one existing shared operation handler into
  several classes merely because its parser has subcommands.

Constructors only save explicitly typed dependencies. Create application services
through narrow factories during execution, after existing guards. Commands adapt
the existing Namespace, call Core use cases and format results; Core retains
domain rules, persistence, lifecycle authority and recovery.

Keep `processforge.py` as the explicit per-call composition root. Do not introduce
a base command hierarchy, DI container, dynamic discovery, whole-Core/module
dependency in registrars, reverse imports or old internal import aliases.
Remaining legacy handlers move with their bounded Core refactors.

Preserve the released CLI contract and original project/distribution identity.
Update actual consumers and payload checksums when moving a module. Use focused
existing checks and equivalence evidence appropriate to the change. Follow the
project's governed Work scope and preserve unrelated working-tree changes.
