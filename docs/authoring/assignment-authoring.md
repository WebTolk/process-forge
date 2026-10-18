# Assignment Authoring

Assignments bound one unit of work and identify its responsible writer. Keep
the objective, authorized read/write scope, required inputs and expected result
explicit. A capsule pins those decisions; a worker cannot widen them itself.

## Choose The Record Format

Use the current schema for the format being authored:

- A YAML task record follows [assignment.schema.json](../../schemas/assignment.schema.json).
  Its required fields are `schema_version`, `id`, `title`, `run_id`, `process`,
  `status`, `iterations` and `result`. `execution_mode`, when present, is an
  object rather than a mode string.
- A Markdown assignment with YAML front matter follows
  [assignment-front-matter.schema.json](../../schemas/assignment-front-matter.schema.json).
  Its required fields include `role`, `stage`, `allowed_files`,
  `forbidden_files` and `required_outputs`, alongside version, id, status and
  process. See [front-matter examples](../concepts/assignment-front-matter.md).
- A prose-only [assignment template](../../templates/assignment-template.md)
  is an authoring checklist. Its headings do not replace machine-readable
  scope or grant execution permissions.

Schema validity alone does not establish executable readiness. Empty grants
grant nothing; specify bounded reads and allowed actions as well as write
paths. Metadata-only resources do not authorize body reads. Required unavailable
inputs block dependent work.

## Authoring Checklist

Capture the following when relevant to the selected process and assignment
format; these are authoring topics, not one universal list of schema fields:

- id
- title
- role
- process id and version
- stage
- goal
- input artifacts
- allowed files
- forbidden files
- required outputs
- required artifacts
- required reviews
- allowed templates
- allowed tools
- quality checklist
- completion criteria
- log file
- handoff requirements
- status

Keep one writer per scope. A delegated package should be cohesive enough for
one responsible writer, with disjoint ownership when other workers run in
parallel. Put repository scratch in a writer-owned directory under `.pf/tmp/`.

For a [prepared worker](../concepts/prepared-input.md), identify the immutable
assignment/context and exact outputs. The worker uses supplied inline inputs
and declared file references without starting another Work or rebuilding
context. State whether the report is written to an authorized artifact path
or captured from the final response; a read-only worker must not write it.
