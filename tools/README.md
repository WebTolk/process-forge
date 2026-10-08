# Tools

ProcessForge tools are local validators and helper scripts for file-only mode.
Runtime usage should prefer the public launcher `python bin/pf.py`.

## Validation Scripts

```bash
python tools/validate-process-forge-schemas.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python tools/validate-public-cleanliness.py --root .
```

## Current CLI Flow

`pf_cli.application.CliApplication` owns the existing single-invocation flow:
argument parsing, mode checks, diagnostic operation and handler dispatch.
`processforge.py:main` composes it for each call using the existing parser and
project identity callback. `processforge.py:build_parser` composes argument
registrars in their existing order. Extracted Work and Agent Entry handlers live
in `pf_cli.commands`; remaining handlers stay in their owning modules. Domain
services remain in
`processforge_core`. CLI modules belong to the shallow `pf_cli` package, with
explicit imports from their owners and minimal package initializers.

`pf_cli.parsers` groups argument registration by responsibility. Registrars
receive explicitly typed handler and value dependencies; their constructors
perform no registration or service calls. `build_parser` binds current values
for each build and supplies the public subparser registration callback.

`pf_cli.parsers.diagnostics.DiagnosticsCommandParser` registers the existing
`diagnostics-configure`, `diagnostics-status` and `diagnostics-export` commands.
`build_parser` constructs it from the existing handlers at their original
registration position. Command-family argument definitions belong to their
owning CLI module; diagnostic policy and storage stay in their existing owners.
Configuration and Egress registration also belong to `pf_cli.parsers`; their
existing command implementations retain their Core calls and guards.

Extracted command adapters belong to `pf_cli.commands`: one concrete class with
`execute(args)` per independent handler, with related classes sharing a module.
The [CLI placement rules](pf_cli/AGENTS.md) apply to future classes as well.

`pf_cli.commands.work` contains the existing start, state, resource-read and
transition adapters, each with its own `execute(args)` class and narrow lazy
Core factory. `pf_cli.commands.agent_entry` contains `AgentEntryCommand` and
`AgentStartPromptCommand`. Existing Core guards, use cases, byte budgets and
result formatting retain their behavior. The root supplies explicit dependencies
and keeps original CLI module identity in service composition.

```bash
python bin/pf.py workplace-init --workplace <workplace-root> --dry-run
python bin/pf.py workplace-init --workplace <workplace-root> --apply
python bin/pf.py doctor-workplace --root <workplace-root>
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --dry-run
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --apply
python bin/pf.py doctor-project --project-root <project-root>
python bin/pf.py project-context-refresh --project-root <project-root>
python bin/pf.py project-context-check --project-root <project-root>
python bin/pf.py assignment-capsule --project-root <project-root> --assignment <assignment-path>
python bin/pf.py doctor-context --project-root <project-root>
```

## Compatibility Commands

`context-resolve` and `context-compile` remain compatibility-only commands. New
project flow should use `project-context-refresh`, `project-context-check`, and
`assignment-capsule`.

The tools use only the Python standard library.
