# Common Evolve Mechanism

`evolve` is a common ProcessForge mechanism for reusable learning extraction.
It is declared as a top-level block in every authored process definition. The
block is process-agnostic: software, testing, content, authoring, setup, and
registration processes all either enable evolve or disable it with a reason.

An enabled process writes local learning artifacts at the configured timing,
usually `end_of_run`:

```text
.pf/artifacts/evolve/
  evolution-report.md
  evolution-report.yaml
  knowledge-candidates/
  instruction-update-proposals/
  process-improvement-proposals/
```

The MVP creates candidates only. It does not train an LLM model, mutate global
packages automatically, or bypass review/export boundaries. Global package
changes happen later through the file-first knowledge hub and existing update
system.

Candidate extraction is target-aware. The process records `source_context`,
`target`, `applicability`, `generalization`, `routing`, and `promotion` for
each candidate so the hub can distinguish where something was observed from
where it should be curated. The extractor defaults to the narrowest safe scope:
project facts stay project-scoped, delivery/build behavior is routed to a
delivery profile, process-flow changes go to a process definition, and platform
constraints go to platform contracts or knowledge packages only when the
applicability block says so.

When an observation contains multiple kinds of reusable knowledge, split it
before export. Do not combine process improvement, platform knowledge, and
delivery-profile policy in one candidate target.

Missing `evolve` is a doctor warning for draft and experimental process
definitions. Public stable catalog validation treats missing `evolve` as a
failure.
