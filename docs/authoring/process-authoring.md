# Process Authoring

Process authoring creates a usable ProcessForge process pack from guided answers.
It writes a private authoring session first, reviews the generated draft, then
applies public process files only after the draft passes blocking checks.

## Commands

```bash
python bin/pf.py process-authoring-start --project-root <project-root> --id seo-audit --title "SEO Audit" --apply
python bin/pf.py process-authoring-review --project-root <project-root> --process seo-audit
python bin/pf.py process-authoring-apply --project-root <project-root> --process seo-audit
python bin/pf.py process-doctor --project-root <project-root> --process seo-audit
```

One-command creation is available when an answers file already exists:

```bash
python bin/pf.py process-create --project-root <project-root> --answers templates/process-authoring-answers.yaml --apply
```

## Authoring Files

The session lives under `.pf/authoring/processes/<process-id>/`:

- `answers.yaml`
- `draft.process.yaml`
- `questions.md`
- `logic-review.md`
- `authoring-log.md`
- `apply-report.md`

Apply writes public files:

- `processes/<process-id>.yaml`
- `prompts/<process-id>-agent.md`
- `docs/processes/<process-id>.md`
- `examples/process-authoring/<process-id>/`

## Logic Review

`process-authoring-review` checks for duplicate ids, missing roles, missing
artifacts, missing gates, gate artifacts that do not exist, handoff before
review, invalid task-loop iteration kinds, private local paths, and secret-like
values.

Warnings are visible in `logic-review.md`; blocking failures stop apply.

## Scope

This MVP creates file-first process packs. It does not add a background runner,
daemon, web transport, command hook execution, GUI, marketplace, database, or
package publishing flow.
