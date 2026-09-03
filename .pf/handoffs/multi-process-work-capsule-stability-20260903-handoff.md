# Handoff: Multi-Process Work Capsule Stability

Status: implementation and focused acceptance complete.

Delivered:

- Additive process-selection mapping with legacy singular-process compatibility.
- Optional explicit `process_id` for Core CLI and `pf.work.start` MCP.
- Compact ambiguity choices, allowlist enforcement, and one pinned active process per Work capsule.
- Pinned active specializations and selected resource IDs; no broad project/process union in the capsule.
- Completion advisory for a new Work, including allowed route recommendation and generated handoff path.
- Schemas, templates, concept documentation, deterministic smoke coverage, and refreshed checksum inventory.
- Real Joomla plugin safe-copy transcript for analysis -> completion -> standalone implementation.

Verification: focused 13-case smoke, affected existing Garage Work-start/state smokes, Python compilation, schema/checksum validators, project doctor, runtime event validation, and real-project acceptance passed.

Residual risks:

- Full public release requalification was not executed.
- The unrelated historical 1.1.0 run-artifact-consistency release blocker remains; this handoff is not public-release approval.
- Candidate metadata is dynamically resolved only to produce the compact choice response; it is not persisted into Work.
- The assurance assignment is procedurally `blocked`: an initial transition referenced nonexistent `tasks.yaml`; a corrected evidence retry satisfies all requirements, but the status is immutable. No state repair was attempted.
