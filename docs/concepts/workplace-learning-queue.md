# Workplace Learning Queue

The workplace learning queue is the durable private queue for evolve
candidates:

```text
<workplace>/learning/
  index.yaml
  inbox/
  bundles/
  exports.ndjson
```

Use:

```bash
python bin/pf.py evolve-candidate-create --project-root <project> --workplace <workplace> --from-file .pf/artifacts/evolve/knowledge-candidates/kc-example.yaml
python bin/pf.py evolve-candidate-list --workplace <workplace>
python bin/pf.py evolve-candidate-export --workplace <workplace> --target docs.example --output learning-export.zip
```

The queue is not runtime cache. Do not store long-term learning only under
`.pf/runtime`.
