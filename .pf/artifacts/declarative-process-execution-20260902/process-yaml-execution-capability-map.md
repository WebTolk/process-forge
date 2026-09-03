# Process YAML Execution Capability Map

Status: ready_for_review
Date: 2026-09-02

| YAML declaration | Current meaning | Execution use |
| --- | --- | --- |
| `id`, `version` | Process identity | Pin identity and version on Run/Assignment |
| `initial_stage` | Not currently defined | Optional explicit initial stage |
| `stages[]` order | Ordered process documentation | Linear default routing |
| `stages[].id` | Stable stage identity | Durable `Assignment.stage` |
| `stages[].executable` | Not currently defined | Skip non-executable stages when false |
| `required_inputs` | Declared semantic inputs | State obligations and transition blockers |
| `produced_artifacts` | Declared semantic outputs | Required transition evidence |
| `entry_gates` | Declared entry constraints | State visibility and target-stage validation |
| `exit_gates` | Declared exit constraints | Blocking transition checks |
| `automation_bindings` | Projector declarations | Deterministic technical blockers |
| `outcomes[]` | Not currently defined | Minimal declarative branching (`id`, `next_stage`) |
| `gates[]` | Gate definitions | Gate metadata and blocking policy |
| `stage_completion` | Process-level completion policy | Stage evidence/history policy |
| `run_completion` | Run completion policy | Final-stage completion checks |
| `process_transitions` | Cross-process handoff routes | Preserved; never used for stage routing |

## Normalized execution definition

The service consumes a deep-copied, JSON-compatible Process definition with:

- executable stages in declared order;
- one validated initial stage;
- gate definitions indexed by id;
- per-stage normalized outcomes;
- a canonical SHA-256 fingerprint of the entire effective definition.

Unknown Process fields remain data and are retained in the pinned definition.
They are not executed.

## Evidence model

Transition evidence is data, not code. Supported evidence records identify a
gate, artifact, input, check, event, or attestation and carry status, summary,
and an optional repository-relative path. If a path is supplied, ProcessForge
verifies that it exists and records its SHA-256 hash. Semantic quality remains
an agent or human judgment represented by an attestation.
