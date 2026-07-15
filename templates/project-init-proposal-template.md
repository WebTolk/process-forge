# Project Init Proposal

## Project

- id: <project-id>
- name: <project-name>
- mode: <greenfield|brownfield>

## Planned Public Files

- .pf/AGENTS.md
- .pf/process-forge.yaml
- .pf/hooks.yaml
- .pf/packages/project.<project-id>.yaml
- .pf/artifacts/project-profile.md
- .pf/artifacts/repository-map.md
- .pf/artifacts/project-conventions.md
- .pf/artifacts/toolchain-detection-report.md
- .pf/artifacts/mcp-capability-report.md
- .pf/artifacts/template-matching-report.md
- .pf/artifacts/global-resource-matching-report.md
- .pf/reviews/project-init-review.md

## Planned Private Files

- .pf/process-forge.local.yaml

## Risks

- Existing files are not overwritten without explicit approval.
- Root project AGENTS.md is not created by default.
- Detection results are observed, not confirmed.

## Recommendation

Review the proposal, then run apply mode if acceptable.
