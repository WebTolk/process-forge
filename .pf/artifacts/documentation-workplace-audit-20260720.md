# Documentation And Workplace Audit - 2026-07-20

## Scope

Audit and align ProcessForge documentation, examples, prompts, installed
workplace distribution, and project onboarding behavior against the current
codebase.

## Documentation Updates

- Rebuilt human-facing `README.md`, `README.ru.md`, `QUICKSTART.md`, and
  `QUICKSTART.ru.md` around the top-down model: workplace device, installed
  ProcessForge tool, global workplace resources, project `.pf/` layer.
- Replaced the architecture SVG with a workplace layout infographic showing
  global `.agents`, ProcessForge tool root, global machine content, and multiple
  project `.pf/` layers.
- Updated agent runbooks to document only implemented commands from
  `tools/processforge.py`.
- Removed stale base-technology platform ids from docs and examples.
- Kept real platform names only as explicit documentation examples of
  parent/child platform composition.
- Fixed stale docs for workplace init, project init, resource management,
  package authoring, template authoring, doctor-context, process events, task
  batch examples, and project/workplace prompts.

## Code Fix

`platform_resource_findings()` now checks template ids from both
`template_roots` and `templates` in `registries/templates.yaml`. Before this
fix, platform contracts could report recommended templates as missing even when
the templates were registered and passed `template-doctor`.

## D:\.agents Update

- `D:\.agents\process-forge` was an installed distribution, not a git checkout.
- Updated it from validated `dist/processforge-v0.1.0.zip`.
- Old installed copies were preserved:
  - `D:\.agents\process-forge.backup-20260720-102521`
  - `D:\.agents\process-forge.backup-20260720-103210`
- Updated `D:\.agents\pf-workplace\registries\distributions.yaml` metadata to
  `version: 0.1.0-rc.1`.

## Workplace Audit

`doctor-workplace --root D:\.agents\pf-workplace` passed after the final
installation.

Knowledge package doctors:

- PASS: all manifest-backed workplace knowledge packages checked during the
  audit.
- Not valid packages: two unmanaged workplace package directories had no
  `package.yaml`.

Platform contract doctors:

- PASS: all manifest-backed workplace platform contracts checked during the
  audit.
- Not a valid contract: one unmanaged workplace platform-contract directory had
  no `platform-contract.yaml`.

Template doctors:

- PASS: `joomla.installer-script`
- PASS: `joomla.module-info-field`
- PASS: `joomla.plugin-info-field`
- PASS: `php.class-docblock`

## Project Onboarding Smoke

Created a no-plugin-code onboarding smoke project:

`D:\Dev\pf-onboarding-smoke\joomla-plugin-like-final-20260720`

Commands:

```bash
python D:\.agents\process-forge\bin\pf.py project-onboard --project-root D:\Dev\pf-onboarding-smoke\joomla-plugin-like-final-20260720 --workplace D:\.agents\pf-workplace --type joomla-plugin --apply
python D:\.agents\process-forge\bin\pf.py doctor-project --project-root D:\Dev\pf-onboarding-smoke\joomla-plugin-like-final-20260720
python D:\.agents\process-forge\bin\pf.py project-context-check --project-root D:\Dev\pf-onboarding-smoke\joomla-plugin-like-final-20260720
```

Result:

- project selected the expected workplace platform through project type hints;
- project snapshot included the expected workplace knowledge package in
  `knowledge_stack`;
- required capabilities resolved;
- no missing recommended template warning after the code fix;
- `project-context-check` returned `RESULT: pass`;
- residual warning: project-local package draft has no resource index yet.

## Validation

- `python -m py_compile tools\processforge.py bin\pf.py`: PASS
- `python tools\validate-process-forge-schemas.py --root .`: PASS
- `python tools\validate-public-cleanliness.py --root .`: PASS
- `python tools\validate-process-forge-checksums.py --root . --write`: updated
- `python bin\pf.py release-test --root .`: PASS
- `python bin\pf.py release-pack --root . --output dist\processforge-v0.1.0.zip`: PASS
- `python bin\pf.py release-archive-test --archive dist\processforge-v0.1.0.zip`: PASS
