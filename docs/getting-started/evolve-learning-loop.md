# Evolve Learning Loop

Minimal local loop:

```bash
python bin/pf.py evolve-run --project-root <project> --workplace <workplace> --process <process> --run <run-id>
python bin/pf.py evolve-candidate-create --project-root <project> --workplace <workplace> --from-file .pf/artifacts/evolve/knowledge-candidates/kc-example.yaml
python bin/pf.py evolve-candidate-export --workplace <workplace> --target docs.example --output learning-export.zip
python bin/pf.py knowledge-hub-init --hub <hub> --apply
python bin/pf.py knowledge-hub-import --hub <hub> --bundle learning-export.zip --apply
python bin/pf.py knowledge-package-build-from-candidates --hub <hub> --package docs.example --version 1.1.0 --apply
python bin/pf.py knowledge-package-release --hub <hub> --package docs.example --version 1.1.0 --output <hub>/packages/docs.example/releases/1.1.0/docs.example-1.1.0.zip
```

Before `evolve-candidate-create`, shape each candidate with:

- `source_context`: process, run, task, platform stack, knowledge stack, and
  package context where the observation came from.
- `target`: the layer and id that should receive the proposed change.
- `applicability`: applies-to, not-applies-to, conditions, and inheritance
  evidence.
- `generalization` and `promotion`: how far the observation may safely travel.
- `routing.recommended_destination`: the package or definition selected by hub
  export/build.

Use the narrowest safe scope by default. Split mixed observations instead of
putting process improvement, platform knowledge, and delivery-profile policy in
one candidate.

After release, use the normal update commands to discover, stage, verify, and
apply the package update. Project context snapshots are not refreshed silently;
existing freshness policy reports whether they are fresh, fresh with updates,
stale, or broken.
