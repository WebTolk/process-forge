# Workplace learning queue

Workplace learning queue - это durable private очередь для evolve candidates:

```text
<workplace>/learning/
  index.yaml
  inbox/
  bundles/
  exports.ndjson
```

Команды:

```bash
python bin/pf.py evolve-candidate-create --project-root <project> --workplace <workplace> --from-file .pf/artifacts/evolve/knowledge-candidates/kc-example.yaml
python bin/pf.py evolve-candidate-list --workplace <workplace>
python bin/pf.py evolve-candidate-export --workplace <workplace> --target docs.example --output learning-export.zip
```

Это не runtime cache. Долгосрочные learning records не должны жить только в
`.pf/runtime`.
