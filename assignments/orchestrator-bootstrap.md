# Assignment: pf-bootstrap-orchestrator - Bootstrap ProcessForge

## Status

completed

## Role

Orchestrator

## Process

- id: knowledge-package-improvement
- version: 0.1.0
- stage: integrate

## Goal

Create the clean-start ProcessForge file-only bootstrap product.

## Input Artifacts

- processforge_master_prompt.md
- internal reference flow summary

## Allowed Files

- README.md
- AGENTS.md
- process-forge.yaml
- docs/**
- schemas/**
- processes/**
- packages/**
- templates/**
- examples/**
- tools/**
- assignments/**
- artifacts/**
- contexts/**
- logs/**
- reviews/**
- handoffs/**
- adr/**
- runtime/**
- private-notes/**
- CHANGELOG.md
- LICENSE
- .processforge-releaseignore

## Forbidden Files

- .idea/**
- .serena/**

## Required Outputs

- clean ProcessForge skeleton
- initial ADR set
- agent assignments
- validation tools
- public cleanliness review
- consolidated roadmap

## Required Artifacts

- artifacts/bootstrap-scope.md
- artifacts/core-file-model.md
- artifacts/status-model.md
- artifacts/consolidated-roadmap.md
- artifacts/changed-files.md

## Required Reviews

- reviews/bootstrap-review.md
- reviews/public-cleanliness-review.md

## Allowed Templates

- assignment-template
- artifact-template
- review-template
- handoff-template
- adr-template

## Allowed Tools

- repository_symbol_analysis
- filesystem_editing
- validator

## Quality Checklist

- Public product has no private source references.
- MVP is file-only and backend-free.
- At least three seed processes exist, including a non-development process.
- Validation scripts run.

## Completion Criteria

- Required files exist.
- Validation evidence is recorded.
- Handoff exists for next work.

## Log File

logs/task-log.md

## Handoff Requirements

- Summarize delivered scope, residual risks, and next recommended actions.
