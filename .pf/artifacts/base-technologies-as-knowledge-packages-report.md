# Base Technologies As Knowledge Packages Report

- timestamp: 2026-07-19 16:41 +04:00
- source assignment: `задания/processforge_base_technologies_as_knowledge_packages_followup_prompt.md`
- status: release_validated

## Decision

Base languages and web technologies are modeled as knowledge packages plus
capabilities, not as platform contracts.

Canonical knowledge package ids:

- `docs.php`
- `docs.web.html`
- `docs.web.css`
- `docs.web.javascript`
- `docs.web.accessibility`
- `docs.web.performance`

Discouraged base-technology platform ids are guarded by CLI warnings and public
release checks. User-created contracts with those ids produce doctor warnings;
built-in/public examples that introduce them as real platforms fail release
validation.

## Platform Model

- `platform.example-parent` directly includes `docs.php`, `docs.web.html`, optional
  `docs.web.css`, `docs.web.javascript`, `docs.web.accessibility`,
  `docs.web.performance`, and `docs.example-parent`.
- `platform.example-parent` declares the matching capabilities: `php`, `html`, `css`,
  `javascript`, `web.accessibility`, and `web.performance`.
- `platform.example-child` extends only `platform.example-parent` and requires
  `platform.example-parent`.
- `platform.example-child` extends only `platform.example-parent` and requires
  `platform.example-parent`.
- Base technology platform contracts are not built in.

## Implementation

- Updated capability seed and manifest-based `platform.example-parent` composition.
- Updated platform contract resolution so top-level `capabilities` and
  `requires.capabilities` both participate in required capability resolution.
- Updated required resource resolution so required `includes.knowledge_packages`
  entries behave as required dependencies.
- Added warning behavior for user-created base technology platform contracts.
- Parent checks for `platform.example-child` and `platform.example-child` were later
  superseded by manifest-only `extends` and `requires.platforms` checks.
- Added public release/example checks for accidental built-in base technology
  platform examples.
- Updated `tools/smoke_platform_inheritance.py` to assert positive inheritance,
  inherited base knowledge packages, no core base platform constants, and
  generic missing dependency behavior.

## Documentation And Examples

- EN/RU README and quickstart now explain capabilities vs knowledge packages vs
  platform contracts.
- EN/RU concept and authoring docs now state that base languages and web
  technologies are not platform contracts.
- Example Parent Platform, Example Child Platform, and Example Child Platform inheritance examples now show base
  technology packages through Example Parent Platform composition.
- Added `examples/knowledge-packages/base-technologies/README.md`.

## Checks Passed

- `python -m py_compile tools/processforge.py tools/smoke_platform_inheritance.py tools/validate-process-forge-schemas.py`
- `python tools/smoke_platform_inheritance.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/processforge.py release-check --root .`
- `python bin/pf.py examples-check --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python bin/pf.py release-test --root .`
- `python bin/pf.py release-pack --root . --output dist/processforge-v0.1.0.zip`
- `python bin/pf.py release-archive-test --archive dist/processforge-v0.1.0.zip`
- `git diff --check`

## Remaining Limitations

- This slice does not introduce complex platform remove/override rules.
- Existing user workplaces may still contain discouraged base technology
  platform contracts; doctors warn but do not delete user-authored resources.
