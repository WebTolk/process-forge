# Release Preparation Run

This example models a release cycle as a concrete run.

```bash
python bin/pf.py run-create --project-root . --id release-preparation --title "Release preparation" --process task-batch-execution --apply
python bin/pf.py task-create --project-root . --run release-preparation --id task-001-clean-docs --title "Clean release docs" --process software-feature-development --apply
python bin/pf.py iteration-add --project-root . --task task-001-clean-docs --kind work --summary "Updated public release docs." --apply
python bin/pf.py iteration-add --project-root . --task task-001-clean-docs --kind debug --status passed --summary "Checked docs for public-safe paths." --apply
python bin/pf.py task-complete --project-root . --task task-001-clean-docs --summary "Release docs are ready." --apply
python bin/pf.py task-create --project-root . --run release-preparation --id task-002-release-test --title "Run release validation" --process testing --apply
python bin/pf.py iteration-add --project-root . --task task-002-release-test --kind test --status passed --summary "Release validation passed." --apply
python bin/pf.py task-complete --project-root . --task task-002-release-test --summary "Release validation complete." --apply
python bin/pf.py run-summary --project-root . --run release-preparation --apply
python bin/pf.py run-complete --project-root . --run release-preparation --apply
```
