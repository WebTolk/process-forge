# Process Authoring

Process authoring creates a usable ProcessForge process pack from guided answers.
It writes a private authoring session first, reviews the generated draft, then
applies public process files only after the draft passes blocking checks.

## Commands

```bash
python bin/pf.py process-authoring-start --project-root <project-root> --id quality-audit --title "Quality Audit" --apply
python bin/pf.py process-authoring-review --project-root <project-root> --process quality-audit
python bin/pf.py process-authoring-apply --project-root <project-root> --process quality-audit
python bin/pf.py process-doctor --project-root <project-root> --process quality-audit
```

One-command creation is available when an answers file already exists:

```bash
python bin/pf.py process-create --project-root <project-root> --answers templates/process-authoring-answers.yaml --apply
```

## Authoring Files

The session lives under `.pf/authoring/processes/<process-id>/`:

- `answers.yaml`
- `draft.process.yaml`
- `questions.md`
- `logic-review.md`
- `authoring-log.md`
- `apply-report.md`

Apply writes public files:

- `processes/user/<process-id>.yaml`
- `prompts/<process-id>-agent.md`
- `docs/processes/<process-id>.md`
- `examples/process-authoring/<process-id>/`

## Contract Vocabulary

`Stage` declares **what** work is required: inputs, produced or required
artifacts, required evidence, and entry/exit gates. `Gate` is the only
blocking decision surface. `artifact_definitions` and `evidence_definitions`
declare the identifiers referenced by a Stage.

Use `exit_gates`, not the legacy `gates` alias. Runtime-specific projectors
belong in `automation_bindings`; they describe **how** an observation is
computed and must not introduce a second blocker list. The former
`technical_obligations` name remains readable only for compatibility.

`process_transitions` describe a Process-to-Process contract. Project-local
`.pf/process-routes.yaml` is the executable route map used by handoffs; it is
not a Stage progression mechanism. An assignment may declare `stage`; Runtime
otherwise uses only an explicit Process `runtime_execution_boundary` mapping
from durable worker status to a Stage.

## Logic Review

`process-authoring-review` checks for duplicate ids, missing roles, missing
artifacts, missing gates, gate artifacts that do not exist, handoff before
review, invalid task-loop iteration kinds, private local paths, and secret-like
values.

Warnings are visible in `logic-review.md`; blocking failures stop apply.

## Evolve Decision

Every standard process-authoring flow must record an explicit top-level
`evolve` decision. Enabled evolve captures reusable learning candidates; disabled
evolve must include a concrete reason.

```yaml
evolve:
  enabled: true
  decision:
    value: enabled
    reason: This process may produce reusable knowledge.
  mode: optional
  timing: end_of_run
  default_scope: project
  candidate_targets:
    - knowledge_package
    - template_package
    - process_definition
  candidate_targeting:
    ask_target_layer: true
    ask_applicability: true
    ask_not_applicable: true
    ask_generalization_level: true
    default_to_narrowest_scope: true
```

The materializer preserves evolve from answers into `processes/user/<process-id>.yaml`.
Do not place evolve only in `metadata`, and do not treat it as software-only,
model training, or automatic global package mutation.

When evolve is enabled, authoring questions must capture candidate targeting.
Ask which target layer receives each candidate, where the observation applies,
where it does not apply, and whether the observation should remain narrow,
split into multiple candidates, or become a promotion proposal. The generated
process keeps:

```yaml
evolve:
  extraction_hints:
    - Split candidates when an observation contains project-specific and platform-general parts.
  candidate_targeting:
    default_scope: project
    require_applicability: true
    require_target: true
    default_to_narrowest_scope: true
```

## Transitions And Agents

Authoring answers should choose `execution_mode` before asking advanced role
questions:

- `single_agent`
- `single_agent_with_subagents`
- `orchestrated_agents`
- `process_factory`

For `single_agent`, ask only about primary-agent artifacts, mandatory gates,
CLI checks, ledger check-in/check-out, and operator approval. Do not ask
Director, Supervisor, route, lease, or external worker questions unless the user
chooses a mode that needs those mechanics.

Authoring answers may include `process_transitions`, `agent_requirements`,
`responsibility_boundaries`, `execution_mode_questions`,
`coordination_requirements`, `error_handling`, and `subagent_policy`.
These fields record whether
the process can hand off work, which target processes and handoff modes are
allowed, which input artifacts and expected output artifacts cross the process
boundary, which receiving role or capability is required, how offline agents
are handled, whether continuation capsules are required, who owns the run after
handoff, and whether shell workers may call subagents.

`responsibility_boundaries` records who coordinates, who verifies runtime
execution, who performs the assigned work, and which CLI checks replace
token-heavy reasoning. Use it to keep Director/Ledger/Inspector/Worker duties
explicit: Director coordinates routes, leases, handoffs, and continuations;
Execution Inspector checks task runtime status, heartbeat, exit, required
outputs, and expected reports; Worker performs the capsule task.

## Coordination Requirements

Process authoring must record how the process behaves in simple and organized
projects:

```yaml
coordination_requirements:
  mode: simple_allowed # simple_allowed | organized_required | organized_optional
  director_inbox:
    required: false
    optional: true
  error_workflow:
    mode: none
error_handling:
  enabled: false
  mode: none
  fallback_if_no_director: needs_operator
```

`organized_required` fails `process-doctor` in an effective simple project
unless the operator uses an explicit override. `simple_allowed` must not require
Director inbox. `organized_optional` adapts to the project's effective mode.

## Scope

This MVP creates file-first process packs. It does not add a background runner,
daemon, web transport, command hook execution, GUI, marketplace, database, or
package publishing flow.
## Specialization Policy

If a process supports specializations, keep `specialization_policy` as optional
routing metadata. Workflow stages should declare abstract
`requires_capabilities`; concrete resource bindings belong to specialization
resources and their `platform_bindings`.
