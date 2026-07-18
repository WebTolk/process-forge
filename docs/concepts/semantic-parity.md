# Semantic Parity

Semantic parity compares workflow meaning rather than serialized YAML bytes.

For processes, the comparison covers:

- identity and purpose
- kind and scope
- run model
- roles
- stages
- artifact definitions
- gates
- emitted events
- required capabilities, packages, templates, and tools
- forbidden actions

The comparison ignores key order, formatting, comments, generated timestamps,
empty default lists, and authoring-session metadata.

Severity:

- `PASS`: no meaningful differences.
- `WARN`: documented differences do not change process behavior.
- `FAIL`: a required stage, gate, artifact, event, dependency, or run model is lost.

Semantic parity is used by backfill audits to prove that ProcessForge's built-in
processes are reproducible through authoring flows or have explicit unsupported
fields before release.
