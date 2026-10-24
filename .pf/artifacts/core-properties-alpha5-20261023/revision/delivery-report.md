# Alpha5 delivery: source and public distribution accepted

R03 supplies one canonical CoreProperties owner to CLI, Runtime, monitor, MCP
and Host. An immutable loaded identity and a live installed identity retain
source/build provenance, including replacement with the same version label.
Missing remote identity remains unknown. Release, component, protocol, Spec and
schema versions remain distinct. Existing lifecycle guards remain in effect.

The corrected source is `af68fecfc539959d2b732e45016f5d09a700ec3d`, tree
`13c36327a4f4aa0561a61e66f822e9230eb503f8`. The independently reviewed delta is
31 files. The annotated tag `v1.3.0-alpha5` points to that exact source on both
providers. The original CP-A5-R01 CODE NO-GO is resolved; the final native
reviewer returned GO/pass with no open findings.

The 1-1-4 engagement used primary integration, four native PF contribution
responsibilities and an independent native final reviewer. Four contribution
Works were cancelled for the explicit corrected-successor handoff; their code
was integrated and reviewed, without claiming retrospective lifecycle acceptance.
The review and generated-receipt remediation Works completed separately.

## Qualification

| Evidence layer | Verified result |
| --- | --- |
| Exact source, registered pytest | 858 passed, 7 existing skips, 383 subtests; Core properties 97 passed |
| Native full source profile | 274/274 PASS, exit 0 |
| Native full extracted archive | Actual native entrypoint exit 0 and explicit full profile PASS; nested count unavailable |
| Actual archive bytes | 1501 entries, all 1500 managed hashes/control/source verified; relocation and default composition pass |
| New owner quality | Ruff/format, strict mypy, Google docstrings and Bandit pass; combined branch coverage 97% |
| Existing affected code debt | Ruff 383 to 381, new findings 0; Runtime mypy 53 to 53, identical diagnostics, raw exit 1 |
| Installed-payload copy | Registered pytest 858 passed, 7 skipped, 383 subtests; all 8 targeted native smokes pass |
| Physical installed Core | 1500 managed hashes pass; library/CLI/strict context/scoped material checks pass |

The repository is not globally lint/type clean. PF-registered Python tooling and
PF-resolved Python/OOP knowledge were used; no dependency installation occurred.
The source assurance and quality reports retain exact gate boundaries.

Archive qualification used the existing native timeout-scale 3 and full test
selection. The initial timeout, subsequent full archive failure and first
source failure remain retained. R3's optional private collector failed to follow
the Windows launcher's delegated subprocess, returning 1; the actual native CLI
returned 0 with the full extracted profile and final RESULT PASS. Both receipts
are retained, separately reconciled in `native-archive-r3-native-result.json`.
No nested count was invented and no product guard or test result was changed.

## Public release and channel

- [GitHub alpha5](https://github.com/WebTolk/process-forge/releases/tag/v1.3.0-alpha5)
- [GitVerse alpha5](https://gitverse.ru/webtolk/process-forge/releases/tag/v1.3.0-alpha5)

Both releases are public prereleases. Downloaded archive and sidecar hashes
match the qualified bytes on both providers. GitVerse uses a token and the
byte-identical `.manifest.json.txt` sidecar alias; remove `.txt` after download.

Archive SHA256:
`5bba94c513b5bbf3261f1c64ca8a8f537b2d8e4aac47d89597a70ba230eb79d3`.
Historical sidecar SHA256:
`8d9ab711c2edda53c1037bb0ddd2bb2972462b34bdd0aa32b6d457606b5027e9`.

Source D was pushed and read back on both dev remotes. C1
`d723ebf0c5dfce1c1ca29b75579211e6972b9bc7` separately delivered the completed
alpha4 reconnect proof. C2 `02f9eccaaae4868b6bfcdfad01889bb61e2228e8` delivered
the alpha5 channel and exact historical sidecar to both dev remotes. Native
manifest validation used the physical installed alpha5 CLI, after reverifying
all installed managed hashes. Earlier alpha rows and stable metadata are
unchanged; GitHub latest stable remains v1.2.0.

The exact-byte sidecar retains CRLF under its own nested `.gitattributes` rule.
The first metadata diff check used the checked-out tree's older attributes and
flagged CRLF. The corrected check uses `git --attr-source=<proposed-tree> diff
--check`; it passes without changing sidecar bytes, root attributes or global
whitespace configuration. The original diagnostic remains retained privately.

Final portable evidence delivery is recorded separately in `final-delivery.json`
with its exact child commit and both remote SHA readbacks. This report does not
claim an as-yet-unwritten self-referential commit identity.

## Device process acceptance remains open

The distinct dev package was installed once, native update
`core-update-20261024T010255Z`. It contains the same qualified ZIP bytes.
All 1500 managed hashes, 21 backup preimages, configuration, unknown files and
eight unrelated-file/main-index preservation hashes pass. Native Workplace
doctor passes, incomplete_update is false and repair reports nothing_to_repair.
The physical alpha5 CLI was used for strict context and metadata validation.

The real post-restart Ledger/hook session was verified. Earlier alpha4 actual
connected-MCP acceptance was completed separately. After the alpha5 apply:

1. The normal Runtime restart was refused with 409
   `runtime_busy_or_activity_unknown`. Partial worker coverage and unknown
   running count do not establish idle. No force, repair or repeated apply ran.
2. The actual connected MCP still predates this apply and returns legacy
   provenance contract 1 with unknown build. Genuine client reconnect and
   subsequent live process/source/build/context/Work/material checks are pending.

The device Work remains in code-assurance with assurance-complete unsatisfied.
Native continuation `alpha5-device-process-acceptance-20261024` is ready, with
all expected artifacts and an exact immutable handoff. Continuation readiness
does not satisfy either live process gate. Scope grants no MCP/client/hooks/
Ledger restart and no forced Runtime operation.

The source CLI's earlier nested-checkout freshness mismatch was traced to two
project-relative classifier provenance strings; classifier bytes and semantics
match. Physical installed alpha5 strict context is fresh/continue/ready on the
existing snapshot, and scoped search is complete. No snapshot/index refresh ran.
Historical global derived-search incompleteness remains disclosed separately.

Only task-owned changes are delivered. The main checkout's seven unrelated
files and standard Git index remain unchanged. Broader OOP epics remain open.
Future hook-attested session discovery is captured in evolution-report.md;
no automatic session fallback or new global policy was implemented.
