# Knowledge Candidates

A knowledge candidate is a sanitized YAML proposal produced by common `evolve`.
It uses `kind: processforge.knowledge_candidate` and records source context,
target, applicability, generalization, routing, summary, evidence, sensitivity,
review state, curation state, promotion state, and release inclusion.

Every candidate answers three separate questions:

- `source_context`: where the observation was seen.
- `target`: where the change is proposed to live.
- `applicability`: where the rule applies, where it does not apply, and under
  which conditions.

The default is the narrowest safe scope. A project observation remains a
project/package/platform-child candidate until broader applicability is
evidenced. If one observation mixes project-specific facts, platform knowledge,
delivery-profile behavior, and process improvement, split it into separate
candidates with separate targets.

Candidate targets are generic:

- `knowledge_package`
- `template_package`
- `process_definition`
- `delivery_profile`
- `project_rule`
- `platform_contract`
- `workplace_rule`
- `core_docs`
- `core_schema`
- `regression_check`

`generalization.level` records whether the candidate is a narrow observation,
project rule, package rule, platform rule, parent-platform candidate,
parent-platform rule, or universal rule. Child-platform observations are not
automatically promoted to a parent platform. Parent-platform candidates require
an explicit `promotion` block; until approved, package builds stage them as
incoming learnings rather than curated rules.

Candidates remain local until an operator queues, sanitizes, exports, imports,
and curates them. Export blocks unsanitized private paths and secret-like
values.
