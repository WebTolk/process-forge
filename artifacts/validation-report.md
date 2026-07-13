# Validation Report: bootstrap-and-init-validation

## Scope

ProcessForge bootstrap product tree.

## Commands

- `python tools/validate-process-forge-schemas.py`
- `python tools/validate-process-forge-checksums.py --write`
- `python tools/validate-process-forge-checksums.py`
- `python tools/validate-public-cleanliness.py`
- `python -m py_compile tools/processforge.py tools/validate-process-forge-checksums.py tools/validate-process-forge-schemas.py tools/validate-public-cleanliness.py`
- `python tools/processforge.py --help`
- `python tools/processforge.py context-resolve --project-root .`
- `python tools/processforge.py session-start --mode resume --project-root .`
- `python tools/processforge.py context-compile --project-root . --assignment assignments/processforge-session-bootstrap-implementation.md --capsule`
- `python tools/processforge.py doctor-context --project-root . --assignment assignments/processforge-session-bootstrap-implementation.md`
- `git diff --check`

## Results

- `PASS: ProcessForge structure and schema syntax checks passed.`
- `PASS: wrote artifacts\checksum-inventory.sha256`
- `PASS: checksum inventory generated.`
- `PASS: public cleanliness checks passed.`
- `py_compile` exited 0.
- `processforge.py --help` exited 0.
- Session/context CLI smoke checks passed.
- `git diff --check` exited 0; Git reported only LF-to-CRLF working-copy warnings.

## Init Smoke Results

- `python tools/processforge.py init-workplace --root <temp-workplace> --dry-run` printed a plan and wrote nothing.
- `python tools/processforge.py init-workplace --root <temp-workplace> --apply` created workplace files.
- `python tools/processforge.py doctor-workplace --root <temp-workplace>` returned PASS checks and a WARN for optional missing MCP providers.
- `python tools/processforge.py init-project --project-root <temp-greenfield> --workplace <temp-workplace>/workplace.yaml --dry-run` planned a greenfield init for a non-existing project root.
- `python tools/processforge.py init-project --project-root <temp-greenfield> --workplace <temp-workplace>/workplace.yaml --apply` created the project layer.
- `python tools/processforge.py doctor-project --project-root <temp-greenfield>` passed.
- Brownfield init preserved an existing `AGENTS.md` by writing `AGENTS.md.candidate`.
- Brownfield `.gitignore` conflicts are candidate-safe; non-conflicting missing `.gitignore` files are created.
- `python tools/processforge.py doctor-project --project-root <temp-brownfield>` passed.
- Edge-case smoke verified that an existing `.gitignore` is preserved and `.gitignore.candidate` is created.
- Edge-case smoke verified that `doctor-project` fails when a non-built-in required capability is unresolved.
- Independent QA review found cache/public inventory handling, `.gitignore` overwrite safety, and required capability doctor gating issues; these were fixed and revalidated.
- Independent QA's apply-approval concern was triaged against the master prompt: `--apply` is explicit apply-mode confirmation, while brownfield overwrite approval remains separate and is enforced by `.candidate`/`--force` behavior.

## Findings

- Initial public-cleanliness run found public wording that used a private-work marker in explanatory text.
- The wording was corrected in `AGENTS.md` and `docs/validation/validation.md`.
- Re-run passed.

## Residual Risks

- YAML validation is structural and does not yet enforce full schema-equivalent semantics.
- Cross-file semantic validation is intentionally minimal in the bootstrap.
- Init resource matching is heuristic and should be hardened after real-world registry data exists.

## Recommendation

Treat the bootstrap as ready for the next hardening pass.
