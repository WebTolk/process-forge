# Session obligation stage remediation

Status: implemented and verified.

`pf.session_context` already exposed `work.stage_id`, but its nested
`work.stage_obligations` payload contained only gate lists. Gate-less stages
therefore looked identical to consumers. The Runtime read adapter now emits
`stage_obligations.stage_id` from the durable active obligation (with the
active work record as a fallback).

This is presentation-only: Core assignments, events, and stage projection
remain the authority. The acceptance fixture proves a durable transition from
`architecture-plan` to `implementation` and observes the nested identity
change.
