# Authoring Parity

Authoring parity checks whether an existing ProcessForge process or resource can
be represented by the current authoring workflows without losing its meaning.

Parity is semantic, not byte-for-byte. YAML key order, comments, formatting,
generated timestamps, empty defaults, and diagnostic metadata are ignored. The
check focuses on ids, purpose, scope, stages, roles, artifacts, gates, emitted
events, run model, requirements, tools, and privacy constraints.

## Commands

```bash
python bin/pf.py process-authoring-import --project-root . --process task-batch-execution --apply
python bin/pf.py process-parity-check --project-root . --process task-batch-execution
python bin/pf.py process-parity-check-all --project-root .
python bin/pf.py authoring-parity-check-all --project-root .
```

Resource parity commands are available for discoverable resources:

```bash
python bin/pf.py template-parity-check --project-root . --template process-agent-prompt
python bin/pf.py knowledge-package-parity-check --project-root . --package process-forge-core
python bin/pf.py platform-parity-check --project-root . --platform platform-contract-joomla
```

If discovery is not available for a resource kind or id, the command records
`SKIP` with a reason instead of silently passing.

## Results

- `PASS`: no meaningful differences.
- `WARN`: differences or unsupported fields are documented and do not change core behavior.
- `FAIL`: a stage, gate, artifact, emitted event, required dependency, or run model is lost.
