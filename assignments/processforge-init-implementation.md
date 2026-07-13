# Assignment: processforge-init-implementation - Implement ProcessForge Init

## Status

completed

## Role

Init Architect / Developer

## Process

- id: project-initialization
- version: 0.1.0
- stage: apply

## Goal

Implement Workplace Init and Project Init models, templates, schemas, process definitions, CLI tooling, doctor checks, examples, and validation reports.

## Input Artifacts

- processforge_init_master_prompt.md
- process-forge.yaml
- AGENTS.md

## Allowed Files

- docs/**
- schemas/**
- templates/**
- processes/**
- tools/**
- examples/**
- artifacts/**
- reviews/**
- assignments/**
- logs/**
- process-forge.yaml
- README.md
- .gitignore

## Forbidden Files

- .git/**
- .idea/**
- .serena/**

## Required Outputs

- Init documentation.
- Init schemas.
- Init templates.
- `tools/processforge.py`.
- Workplace and project initialization processes.
- Validation evidence.

## Required Reviews

- reviews/init-implementation-review.md

## Quality Checklist

- Dry-run does not write files.
- Apply mode writes expected files.
- Brownfield conflicts create `.candidate` files.
- Public manifests contain no local absolute paths.
- Doctor commands report PASS/WARN/FAIL.

## Completion Criteria

- Local smoke tests pass.
- Public cleanliness passes.
- Validation report is updated.

## Log File

logs/task-log.md

## Handoff Requirements

- Summarize residual risks and next hardening steps.
