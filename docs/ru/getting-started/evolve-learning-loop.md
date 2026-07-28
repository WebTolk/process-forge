# Evolve learning loop

Минимальный локальный цикл:

```bash
python bin/pf.py evolve-run --project-root <project> --workplace <workplace> --process <process> --run <run-id>
python bin/pf.py evolve-candidate-create --project-root <project> --workplace <workplace> --from-file .pf/artifacts/evolve/knowledge-candidates/kc-example.yaml
python bin/pf.py evolve-candidate-export --workplace <workplace> --target docs.example --output learning-export.zip
python bin/pf.py knowledge-hub-init --hub <hub> --apply
python bin/pf.py knowledge-hub-import --hub <hub> --bundle learning-export.zip --apply
python bin/pf.py knowledge-package-build-from-candidates --hub <hub> --package docs.example --version 1.1.0 --apply
python bin/pf.py knowledge-package-release --hub <hub> --package docs.example --version 1.1.0 --output <hub>/packages/docs.example/releases/1.1.0/docs.example-1.1.0.zip
```

После release используйте обычные update commands: discover, stage, verify,
apply. Project context snapshots не обновляются молча; существующая freshness
policy показывает fresh, fresh_with_updates, stale или broken.

## Candidate shape

Перед `evolve-candidate-create` оформите candidate с явными полями:

- `source_context`: process, run, task, platform stack, knowledge stack и
  package context, где найдено наблюдение.
- `target`: слой и id, куда предлагается изменение.
- `applicability`: applies-to, not-applies-to, conditions и inheritance
  evidence.
- `generalization` и `promotion`: насколько далеко наблюдение можно безопасно
  обобщить.
- `routing.recommended_destination`: package или definition, который выберет
  hub export/build.

По умолчанию выбирайте самый узкий безопасный scope. Смешанные наблюдения
разбивайте вместо того, чтобы объединять process improvement, platform
knowledge и delivery-profile policy в одном candidate.
