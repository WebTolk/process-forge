# Release Preparation Run

This example models a release cycle as a concrete run. Run it from any
directory by pointing the ProcessForge launcher at an already onboarded project.

```bash
python <processforge-root>/bin/pf.py run-create --project-root <project-root> --id release-preparation --title "Release preparation" --process task-batch-execution --apply
python <processforge-root>/bin/pf.py task-create --project-root <project-root> --run release-preparation --id task-001-clean-docs --title "Prepare first artifact" --process task-batch-execution --apply
python <processforge-root>/bin/pf.py iteration-add --project-root <project-root> --task task-001-clean-docs --kind work --summary "Updated public release docs." --apply
python <processforge-root>/bin/pf.py iteration-add --project-root <project-root> --task task-001-clean-docs --kind debug --status passed --summary "Checked docs for public-safe paths." --apply
python <processforge-root>/bin/pf.py task-complete --project-root <project-root> --task task-001-clean-docs --summary "Release docs are ready." --apply
python <processforge-root>/bin/pf.py task-create --project-root <project-root> --run release-preparation --id task-002-release-test --title "Validate result" --process task-batch-execution --apply
python <processforge-root>/bin/pf.py iteration-add --project-root <project-root> --task task-002-release-test --kind test --status passed --summary "Release validation passed." --apply
python <processforge-root>/bin/pf.py task-complete --project-root <project-root> --task task-002-release-test --summary "Release validation complete." --apply
python <processforge-root>/bin/pf.py run-summary --project-root <project-root> --run release-preparation --apply
python <processforge-root>/bin/pf.py run-complete --project-root <project-root> --run release-preparation --apply
```
