# ADR: Config-Driven Behavior Contract

Status: accepted
Date: 2026-07-26

## Problem

Config that is accepted but ignored creates false automation guarantees. In the shell-agent orchestration layer this can make a plan appear to allow overlap or require subagent reports while generated assignments, capsules, supervisor scheduling, or collection checks behave differently.

## Decision

Every public config field must have one explicit outcome:

- affect runtime or materialized file behavior
- be documented as metadata-only
- fail validation when unsupported

Unsupported public fields fail validation unless they are placed in an explicit extension namespace such as `metadata` or `x_`.

## Apply Pipeline

ProcessForge resolves complex plans through this pipeline:

1. parse
2. normalize
3. validate
4. resolve defaults
5. materialize assignments, capsules, leases, handoffs, and launch prompts
6. execute or supervise workers
7. verify outputs

## Behavior Trace

Complex shell-agent plans write a behavior trace:

- `.pf/runs/<run-id>/orchestrator-shell-plan.normalized.yaml`
- `.pf/runs/<run-id>/config-resolution-report.yaml`

The report records the resolved overlap policy, runtime driver, supervisor start behavior, worker outputs, and subagent-report policy.

## Public Smokes

Public smoke tests must include config-behavior contracts. The release gate includes `tools/smoke_config_behavior_contracts.py` and the shell-agent smoke asserts resolved config behavior instead of checking only that files exist.
