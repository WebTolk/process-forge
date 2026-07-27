# Software Feature Development

## Purpose

`software-feature-development` is a neutral software lifecycle process. It
guides work from orchestration and intake through investigation, domain
understanding, architecture, implementation, assurance, release delivery, and
evolution capture.

Release and evolution are part of the lifecycle, but they are conditional. A
small local task can mark `release-delivery` as `not_applicable` with a reason
and evidence. Optional stages must not be silently skipped.

## Lifecycle Modes

- `full`: full lifecycle from intake to evolve.
- `feature`: normal feature development with optional release/evolve.
- `bug_fix`: focused investigation, impact analysis, implementation, regression assurance, and optional release notes.
- `debug_loop`: repeated investigation/implementation/assurance; release/evolve optional.
- `implementation_only`: allowed only when scope, investigation, and implementation plan already exist or are explicitly provided.

## Stages

- `orchestration`: select lifecycle mode, context snapshot, coordination mode, assignment/run/task ids, and delivery profile availability.
- `intake-scope`: capture objective, boundaries, non-goals, acceptance criteria, risks, and release requirement.
- `investigation`: inspect code, configs, tests, docs, compatibility, migration risk, and evidence paths.
- `domain-modeling`: capture domain terms and rules from project context and platform contracts.
- `architecture-plan`: define architecture, implementation plan, decision log, verification outline, and rollback concerns.
- `implementation`: make bounded changes and record changed files.
- `code-assurance`: review behavior, tests, risks, and conditional browser/UI verification.
- `release-delivery`: prepare package/patch/release evidence or record not_applicable.
- `evolve`: capture lessons learned and proposals for rules, instructions, knowledge, checks, or delivery profiles.

## Delivery Boundary

Delivery/build/package/install is an operation profile, not a separate
ProcessForge process. Platform-specific delivery belongs in project or platform
profiles:

```yaml
process_id: software-feature-development
execution_profile:
  delivery_profile: project.default_delivery
```

Do not add platform-specific public core processes such as
`joomla-plugin-delivery`. A Joomla, WordPress, Laravel, or other platform
project can define its own delivery profile through platform contracts or
project-local configuration.

## Legacy Mapping

| Legacy concept | ProcessForge concept |
| --- | --- |
| orchestration | `orchestration` |
| intake | `intake-scope` |
| investigation | `investigation` |
| domain | `domain-modeling` |
| architecture | `architecture-plan` |
| implementation | `implementation` |
| assurance | `code-assurance` |
| release | `release-delivery` |
| evolve | `evolve` |
| `updated-cursor` | `instruction-update-proposal` |
| delivery/build runner | delivery/build profile, not process |

## CLI Checks

```bash
python bin/pf.py process-doctor --project-root . --process software-feature-development --contract-only
python bin/pf.py builtin-process-catalog-doctor --root . --public
```
