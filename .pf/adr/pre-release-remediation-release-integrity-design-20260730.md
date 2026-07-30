# ADR: release integrity, provenance, launcher recovery and archive boundary

- ADR id: `pre-release-remediation-release-integrity-design-20260730`
- Date: 2026-07-30
- Status: accepted for Phase A; target version pending for Phase B
- Run: `pre-release-remediation-20260730`
- Assignment: `remediation-release-integrity-design-20260730`
- Related findings: `PF-AUD-014`, `PF-AUD-016`, `PF-AUD-018`,
  `PF-AUD-023`, `PF-AUD-025`
- Extends:
  `.pf/adr/pre-release-remediation-schema-authority-20260730.md`,
  Decisions 7 and 8

## Context

The current release path has five mutually reinforcing gaps:

1. `inspect_release_archive` compares the manifest and ZIP entry names, but
   consumer-only mode does not verify the ZIP hash or entry bytes.
2. `command_release_pack` writes a sidecar with only `name`, `version`,
   `generated_at` and `files[path, sha256]`; it does not identify the source
   commit, source tree, dirty state or the final ZIP.
3. The generated project launcher selects a configured path before checking
   whether it contains the ProcessForge CLI, so a stale project override blocks
   valid workplace and environment fallbacks.
4. `release_source_files` maps `.pf/AGENTS.md` to archive-root `AGENTS.md` and
   also ships three project `.pf` files. The extracted distribution therefore
   presents an incomplete copy of the ProcessForge development project as if it
   were an onboarded project.
5. Product version, changelog, update index and archive version are independent
   mutable declarations. The current public metadata still identifies `1.0.0`,
   does not describe the current official pack slice and contains
   `example.com` update URLs.

The accepted schema-authority ADR establishes that manifest v1 must be
consumer-verifiable, public packing requires a clean Git source state, stale
launcher candidates fall through, and publisher authenticity is outside this
slice. This ADR makes those decisions implementable.

The checksum-surface and installation-documentation slice completed earlier in
this run remains authoritative. Its general `public_file_entries()` alias
mechanism, complete public-directory coverage, sibling workplace/project paths,
and two-step production profile instructions must be preserved. Only the
archive-visible `AGENTS.md` selector and removal of project `.pf` entries need
to be adapted to the boundary decided here.

## Decision 1: release manifest v1

`schemas/release-manifest.schema.json` is the authoritative sidecar contract.
The public manifest has this closed shape; every object uses
`additionalProperties: false`:

```json
{
  "schema_version": 1,
  "name": "processforge",
  "version": "1.0.0",
  "schema_bundle_version": "1.0",
  "release_eligible": true,
  "build": {
    "source_date_epoch": 1785398400,
    "generated_at": "2026-07-30T08:00:00Z",
    "deterministic": true
  },
  "source": {
    "vcs": "git",
    "commit": "<40 lowercase hex>",
    "tree": "<40 lowercase hex>",
    "dirty": false
  },
  "archive": {
    "filename": "processforge.zip",
    "format": "zip",
    "size": 123456,
    "sha256": "<64 lowercase hex>",
    "entry_count": 783
  },
  "official_packs": [
    {
      "id": "processforge.official.software-development",
      "version": "1.0.0",
      "manifest_path": "packs/official/software-development/package.yaml",
      "manifest_sha256": "<64 lowercase hex>"
    }
  ],
  "files": [
    {
      "path": "AGENTS.md",
      "size": 1234,
      "sha256": "<64 lowercase hex>"
    }
  ]
}
```

The example version and counts are illustrative, not a release-version
decision. Semantic checks beyond JSON Schema are mandatory:

- `files` is sorted by `path`; paths are unique after separator normalization,
  Unicode NFC normalization and case folding;
- `archive.entry_count == len(files)` and equals the number of physical ZIP
  members;
- each file size and hash equals the actual uncompressed bytes;
- `archive.size` and `archive.sha256` identify the final sidecar-adjacent ZIP;
- `official_packs` is sorted by `id` and exactly equals valid
  `packs/official/*/package.yaml` manifests with `origin: official`;
- `generated_at` is derived from `source_date_epoch`; it is not wall-clock
  `now_utc()` output;
- a public manifest requires `release_eligible: true`,
  `source.vcs: git`, non-null commit/tree and `source.dirty: false`.

An explicit `release-pack --allow-dirty-non-public` mode may create a
development archive. It must set `release_eligible: false` and
`source.dirty: true`; if Git provenance is unavailable, commit and tree may be
null under the schema's non-public conditional. Such an artifact is rejected by
public release delivery.

Pre-release sidecar shapes are invalid on every read path. There is no
inventory-only compatibility reader and no compatibility synthesis.

This contract proves consistency of the ZIP/manifest pair. An attacker who can
replace both files can create a new internally consistent pair. Publisher
authenticity therefore requires an external signature or trusted publication
channel and remains explicitly out of scope.

## Decision 2: deterministic publisher and provenance

`release-pack` is a public publisher by default:

1. Read and validate all release metadata and the complete source file set.
2. Require a Git worktree with clean tracked and untracked state before any
   output mutation.
3. Capture `HEAD`, `HEAD^{tree}` and the source commit timestamp.
4. Use `SOURCE_DATE_EPOCH` when explicitly supplied; otherwise use the captured
   commit timestamp. Reject invalid or pre-1980 ZIP timestamps.
5. Stage ZIP and manifest in the output directory.
6. Write members in archive-path order with canonical `ZipInfo`: normalized
   POSIX name, fixed timestamp, fixed regular-file mode, empty extra/comment,
   fixed compression and compression level.
7. Hash the same bytes that are written and record size/hash per member.
8. Close the ZIP, compute final ZIP size/SHA-256, then write manifest v1.
9. Re-validate the staged pair in consumer-only mode.
10. Atomically replace the ZIP, then its manifest last. On failure, remove
    staged files and do not publish a new manifest.

The source commit recorded in the manifest is the clean commit from which the
archive was built. If `dist/**` is tracked, a later artifact-only commit does
not rewrite that source provenance: reproduction checks out the recorded
source commit and applies the recorded source-date value. Public automation
should preferably build into an external artifact directory to avoid making
the source checkout dirty during assurance.

Two builds from the same source commit and source-date value in the supported
toolchain must produce the same ZIP SHA-256. The manifest also records
`deterministic: true`; failure of the reproducibility smoke is a release
blocker.

## Decision 3: consumer verification and safe extraction

`inspect_release_archive` becomes the single consumer verifier. It must not
require `--root`. Verification order is:

1. read the sidecar as UTF-8 JSON and validate release-manifest v1;
2. verify declared ZIP filename, byte size and whole-file SHA-256;
3. open the ZIP and inspect every physical `ZipInfo` member;
4. reject unsafe members before reading or extracting any payload;
5. compare actual members with manifest `files` and all three counts;
6. stream each physical member by `ZipInfo`, checking declared size and SHA-256;
7. only after all checks pass, allow extracted-archive tests.

Pre-extraction rejection is mandatory for:

- empty names, NUL/control characters, absolute POSIX paths, drive-qualified
  paths and UNC paths;
- backslashes, or traversal that appears after backslash-to-slash
  normalization;
- empty, `.` or `..` path segments;
- duplicate raw names, duplicate normalized names, Unicode-normalized
  collisions and case-fold collisions;
- explicit directory entries and every symlink, device, FIFO, socket or other
  special entry; manifest v1 archives contain regular files only;
- encrypted members or members whose declared/actual sizes are inconsistent.

Implementation uses `ZipFile.infolist()` and streams by `ZipInfo`; it must not
build a dictionary keyed only by `name`, because that hides duplicate entries.
`extractall()` is forbidden until the verifier has returned PASS. Safe
extraction may then use the already validated normalized paths.

`archive_manifest_freshness_checks(--root)` remains an additional publisher
reproduction check. It is not a substitute for consumer verification and must
reuse the same path/hash primitives.

## Decision 4: linked launcher candidate policy

The standalone Python text produced by `project_runtime_launcher_files` keeps
this precedence:

1. project-local `process_forge.distribution_override`;
2. the `processforge` entry in the linked workplace distribution registry;
3. `PROCESSFORGE_HOME`.

Selection and validation are one operation. A candidate is valid only when its
resolved root is a directory and `<root>/tools/processforge.py` is a regular
file. Missing configuration, malformed/unreadable registry data, path
resolution failure, missing root and missing CLI are candidate rejection
reasons, not terminal selection.

The resolver returns the first valid candidate and a complete ordered
diagnostic list. If a lower-precedence candidate wins, stderr contains one
concise warning for every rejected higher-precedence candidate, the winning
source, and a repair command. Where workplace and project type can be read, the
repair command is the existing:

```text
python <winning-root>/bin/pf.py project-onboard \
  --project-root <project-root> \
  --workplace <workplace-root> \
  --type <existing-project-type> \
  --apply --force
```

If those values cannot be determined, the diagnostic prints the equivalent
command with explicit placeholders and the exact local configuration path.
The launcher never rewrites project or workplace files automatically.

When no candidate is valid, exit is nonzero and the failure lists all three
sources, raw/resolved paths when available, and rejection reasons. Duplicate
resolved paths may be probed once, but each configured source remains visible
in diagnostics.

## Decision 5: distribution is not an onboarded project

Add one authored instruction source:

```text
packaging/distribution-AGENTS.md
```

`release_source_files` maps that file to archive path `AGENTS.md`.
Archive-root `AGENTS.md` is never synthesized from `.pf/AGENTS.md`. The
instruction identifies the root as a replaceable ProcessForge distribution,
directs operators to `bin/pf.py`, and requires workplace/project roots outside
the installation. It does not require an active assignment, ECP, project log,
review or handoff inside the extracted root.

The following source-repository dogfooding files are not archive members:

```text
.pf/AGENTS.md
.pf/process-forge.yaml
.pf/hooks.yaml
```

They remain valid in the ProcessForge development checkout and are not deleted.
The packer's `RELEASE_PF_PUBLIC_FILES`/required-path contract is removed, and
`.pf/` is excluded from the distribution surface.

The existing checksum `public_file_entries()` abstraction is preserved.
Its archive-visible `AGENTS.md` alias must select:

1. `packaging/distribution-AGENTS.md` in a source checkout;
2. `AGENTS.md` in an extracted distribution.

It must no longer select `.pf/AGENTS.md` or add project `.pf` paths. The
accepted root/public-directory/checksum-self-exclusion behavior is unchanged.
Schema/public-cleanliness validators use the same source-vs-extracted alias
contract rather than reintroducing a second file list.

The clean archive acceptance flow is:

- `doctor-project --project-root <extracted-root>` fails explicitly because the
  distribution is not an onboarded project;
- `bin/pf.py --help`, `version` and release checks operate as distribution
  commands;
- `workplace-init` to an external sibling root passes;
- `project-onboard` to another external sibling root passes;
- the generated project runtime launcher and `doctor-project` pass inside that
  onboarded project.

## Decision 6: release metadata authority

`VERSION` is the sole product-version input. `PROCESSFORGE_VERSION` and
`RELEASE_ARCHIVE_VERSION` must not be independently mutable declarations;
version output and release manifest read the validated `VERSION` value.

Before public packing, `release_metadata_checks` requires:

- `VERSION` is valid SemVer;
- the newest `CHANGELOG.md` release heading equals `VERSION`, has an intentional
  release date and describes the official bundled-pack/remediation slice;
- `.pf/process-forge.yaml` in the source checkout declares the same installed
  ProcessForge version;
- `updates/processforge-update-index.yaml` passes its schema,
  `product.current_version` equals `VERSION`, the selected channel's `latest`
  equals `VERSION`, and exactly one version record exists with non-empty
  changes and a valid migration-guide reference when required;
- enabled official update sites use real HTTPS publication URLs; placeholder
  `example.com` URLs are a public-release FAIL;
- release-manifest version equals `VERSION`;
- official-pack inventory equals the current official manifests.

`1.0.0` is already recorded as released on 2026-07-20 and must not be silently
republished with different contents. A new target version is required. The
minimum compatible choice is `1.0.1`; the recommended choice is `1.1.0` if the
new bundled official packs are being introduced as user-visible functionality.
The orchestrator/release owner must record the target decision before the
metadata phase. This ADR does not choose it by inference.

## Exact implementation symbols

The exclusive implementation writer owns these existing symbols in
`tools/processforge.py`:

- constants `PROCESSFORGE_VERSION`, `PROCESSFORGE_SCHEMA_BUNDLE_VERSION`,
  `RELEASE_NAME`, `RELEASE_ARCHIVE_VERSION`;
- `project_runtime_launcher_files` and the generated launcher's
  `distribution_from_workplace`, `distribution_root`, `main`;
- `RELEASE_PF_PUBLIC_FILES`, `RELEASE_REQUIRED_PATHS`;
- `release_source_files`, `release_required_path_exists`, `release_checks`,
  `public_release_checks`;
- `command_version`, `command_release_pack`, `archive_manifest_path`;
- `inspect_release_archive`, `expected_release_manifest_from_root`,
  `archive_manifest_freshness_checks`, `command_release_archive_test`;
- release CLI parser declarations for `release-pack` and
  `release-archive-test`.

It introduces reusable symbols with these responsibilities:

- `release_version(root)`;
- `release_metadata_checks(root, version)`;
- `release_git_provenance(root, allow_dirty_non_public)`;
- `release_source_date_epoch(provenance)`;
- `release_official_pack_inventory(root)`;
- `release_zip_info(path, source_date_epoch, executable)`;
- `write_release_archive(staged_zip, files, source_date_epoch)`;
- `validate_archive_member(info, seen_raw, seen_normalized, seen_casefold)`;
- `load_release_manifest_v1(path)`;
- `verify_release_archive_pair(archive_path, manifest_path)`.

Names may change during implementation, but the responsibilities may not be
folded back into duplicated ad-hoc checks.

## Test matrix

| Contract | Positive evidence | Required negative evidence |
|---|---|---|
| Consumer pair | Valid v1 ZIP/manifest passes without `--root` | Changed member, changed ZIP tail, wrong ZIP size/hash, wrong entry size/hash/count and malformed manifest each fail |
| Name safety | Sorted regular POSIX files pass | Absolute, drive, UNC, `..`, backslash traversal, raw duplicate, normalized duplicate, casefold/NFC collision, symlink and special entry fail before extraction |
| Reproducibility | Two builds from same clean commit and source date have identical ZIP SHA-256 | Wall-clock or file mtime changes do not change output; invalid source date fails |
| Provenance | Clean Git source records exact HEAD/tree and `dirty: false` | Dirty tracked and untracked state blocks public pack; explicit non-public mode records ineligible/dirty |
| Launcher | Valid override wins; stale override falls to workplace; stale override+workplace fall to env | All invalid exits nonzero with all reasons; fallback leaves config and registry byte-identical |
| Relocation | Existing project works after distribution relocation and workplace registry repair | Stale project override does not mask repaired registry/env |
| Archive boundary | Root authored AGENTS, no `.pf/**`; external workplace/project onboarding and project doctor pass | Extracted-root project doctor fails as non-project; root AGENTS never equals project `.pf/AGENTS` by fallback |
| Metadata | All version/changelog/update/manifest values agree and official packs are complete | Reused released version, placeholder URL, missing changelog/update record, duplicate version record and pack mismatch fail |

New focused smokes should be public release checks:

- `tools/smoke_release_archive_manifest_v1.py`;
- `tools/smoke_release_archive_unsafe_entries.py`;
- `tools/smoke_release_reproducibility.py`;
- `tools/smoke_linked_launcher_relocation.py`;
- `tools/smoke_clean_distribution_boundary.py`;
- `tools/smoke_release_metadata_coherence.py`.

`tools/smoke_first_run.py` must invert its current stale-override expectation:
with a valid workplace or environment fallback it expects success and
diagnostics, not `FAIL: ProcessForge CLI not found`.

## Sole-writer and sequencing policy

No two agents edit release selectors or `tools/processforge.py` in parallel.
Execution is sequential:

### Phase A — integrity/launcher/boundary implementation

One writer owns:

- `tools/processforge.py`;
- `schemas/release-manifest.schema.json`;
- `packaging/distribution-AGENTS.md`;
- `.processforge-releaseignore`;
- `tools/validate-process-forge-schemas.py`;
- `tools/validate-public-cleanliness.py`;
- the already changed `tools/validate-process-forge-checksums.py` and
  `tools/smoke_remediation_checksum_surface.py`, preserving their accepted
  coverage logic while changing only the AGENTS alias and `.pf` surface;
- `tools/smoke_first_run.py`;
- the six focused smokes listed above.

`checksums/processforge.sha256`, `dist/**`, `VERSION`, `CHANGELOG.md` and
`updates/**` are forbidden in Phase A.

### Phase B — release metadata

After Phase A review and explicit target-version decision, one metadata writer
owns:

- `VERSION`;
- `CHANGELOG.md`;
- `updates/processforge-update-index.yaml`;
- a target-version migration guide when required;
- `.pf/process-forge.yaml` version fields.

No archive or checksum regeneration occurs in Phase B.

### Phase C — release finalization

After source freeze and review, one release owner:

1. commits the source/metadata state;
2. refreshes `checksums/processforge.sha256`;
3. verifies checksum/public/schema/metadata gates;
4. builds `dist/processforge.zip` and
   `dist/processforge.manifest.json` from the recorded clean source commit;
5. runs consumer-only, extracted quick and extracted full archive tests;
6. records exact source commit/tree, artifact hash/count and any artifact-only
   delivery commit.

`dist/**` is never rebuilt by a parallel implementation worker.

## Consequences

Manifest v1 intentionally rejects the current pre-release sidecar. The current archive
cannot be called consumer-verifiable until rebuilt after all remediation
slices. Existing installed projects remain compatible: their project-local
`.pf` files are unchanged, while the generated launcher becomes resilient to
distribution relocation.

The distribution archive becomes an installable tool root rather than a
truncated copy of the ProcessForge development project. Source dogfooding
remains in the repository and outside the public ZIP.

Public release remains blocked until a new version and real update publication
metadata are chosen. No implementation agent may resolve that product decision
by silently reusing `1.0.0`.
