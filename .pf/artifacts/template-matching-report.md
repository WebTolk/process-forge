# Template Matching Report

Reviewed on 2026-09-27 against the pinned software-feature-development process.

| Required template | Repository source | Application |
| --- | --- | --- |
| assignment-template | `templates/assignment-template.md` | Standard Work CLI generates assignment state |
| artifact-template | `templates/artifact-template.md` | Metadata, summary, content and review in all 29 current artifacts |
| review-template | `templates/review-template.md` | New artifact-completion review |
| handoff-template | `templates/handoff-template.md` | New task completion handoff |

The flow manifest maps templates to the distribution `templates/` directory.
The project `.pf/templates/` contains no local override files at this review.
Project profile, conventions and map follow the corresponding template purpose,
with actual source-backed content replacing generated detection placeholders.

Adaptation: body checksums in the new artifact bundle have explicit
`content_section_utf8_lf` scope to avoid a recursive whole-file hash. PF records
whole-file hashes separately when evidence is submitted. Self-review is labelled
as such; no human approval is invented. Optional outputs state applicability and
the reason instead of leaving template tokens or empty headings.

Do not use domain templates as a substitute for the pinned process. Global
legacy development-flow skills, Joomla overlays and unrelated artifact-template
creation workflows are not required here.

Sources: [artifact template](../../templates/artifact-template.md),
[process](../../packs/official/software-development/processes/software-feature-development.yaml),
[current artifact index](artifact-completion-20260927/README.md).
