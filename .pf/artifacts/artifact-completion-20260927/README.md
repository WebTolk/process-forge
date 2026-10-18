# Complete artifact set

This is the current artifact-completion Work. Artifact status is ready_for_review with explicit primary-agent self-review; no human approval is implied. Historical delivery evidence is linked in [coverage.md](coverage.md).

[Project classification confirmation](project-classification-addendum.md) supplies the reviewed interpretation of the generated onboarding reports.

## Artifacts by stage

| Stage | Artifact | Requirement |
| --- | --- | --- |
| orchestration | [task-record](task-record-r02.md) | required |
| orchestration | [execution-context-summary](execution-context-summary-r02.md) | required |
| orchestration | [lifecycle-mode-decision](lifecycle-mode-decision-r02.md) | required |
| intake-scope | [brief](brief.md) | required |
| intake-scope | [scope](scope.md) | required |
| investigation | [investigation-report](investigation-report.md) | required |
| investigation | [impact-analysis](impact-analysis.md) | required |
| domain-modeling | [domain-notes](domain-notes.md) | required |
| domain-modeling | [domain-model](domain-model.md) | required |
| domain-modeling | [domain-rules](domain-rules.md) | required |
| architecture-plan | [architecture](architecture.md) | required |
| architecture-plan | [implementation-plan](implementation-plan.md) | required |
| architecture-plan | [decision-log](decision-log.md) | required |
| implementation | [changed-files](changed-files.md) | required |
| implementation | [change-summary](change-summary.md) | required |
| code-assurance | [review-findings](review-findings.md) | required |
| code-assurance | [test-plan](test-plan.md) | required |
| code-assurance | [test-cases](test-cases.md) | required |
| code-assurance | [test-report](test-report.md) | required |
| code-assurance | [browser-verification-report](browser-verification-report.md) | conditional; applicability stated |
| release-delivery | [release-notes](release-notes.md) | conditional; applicability stated |
| release-delivery | [migration-notes](migration-notes.md) | conditional; applicability stated |
| release-delivery | [patch](patch.md) | conditional; applicability stated |
| release-delivery | [delivery-plan](delivery-plan.md) | conditional; applicability stated |
| release-delivery | [delivery-report](delivery-report.md) | conditional; applicability stated |
| evolve | [evolution-report](evolution-report.md) | required |
| evolve | [updated-rules-or-extensions](updated-rules-or-extensions.md) | conditional; applicability stated |
| evolve | [instruction-update-proposal](instruction-update-proposal.md) | conditional; applicability stated |
| evolve | [knowledge-update-proposal](knowledge-update-proposal.md) | conditional; applicability stated |

## Provenance and correction

The first orchestration text passed through a PowerShell ASCII pipe and lost non-ASCII characters. Its three original files remain unchanged because a transition recorded their hashes. The effective task-record, execution-context-summary and lifecycle-mode-decision are the readable r02 files linked above and attached as normal intake evidence. Do not use the damaged first capture as current instructions.

[Baseline](baseline.json) and before/ retain original project reports and protected-file hashes. [Coverage JSON](coverage.json) records existing evidence, including pre-existing older hash differences. Private helpers reproduce the inventory and checks; they are not product changes.
