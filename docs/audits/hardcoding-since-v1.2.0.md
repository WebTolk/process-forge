# Hardcoded assumptions since ProcessForge 1.2.0

The audit found a release-selection policy defect and a separate question about
which component owns Work when the project's mode and the transport routing
disagree. The remaining findings are bounded follow-ups. The report records
evidence and a completion criterion for each.

## Revisions and coverage

| Boundary | Git revision |
|---|---|
| Published `v1.2.0` tag, peeled commit | `b70df739700f1559570f4b65481cd39616ccc1ea` |
| Accepted `dev` at the audit cutoff | `03cd92913007df41a907bdd2d41fa6bc741c729a` |
| Accepted Git tree | `478dc9dc0227683ab6d2960df985204d4e7724a8` |

The baseline is an ancestor of the cutoff. A no-renames diff gives 506 additions,
374 modifications and 6,480 deletions. The deleted paths belonged to historical
PF state. The current side contains 880 changed text files and no changed
binary files.

| Current scope | Added | Modified | Reviewed paths |
|---|---:|---:|---:|
| Python outside `tests/` | 229 | 253 | 482 |
| `tests/` | 172 | 0 | 172 |
| Other source, configuration, templates, launchers, CI and docs | 105 | 121 | 226 |
| **Total** | **506** | **374** | **880** |

The Python pass parsed all 482 files and examined 57,658 AST literals
intersecting 100,044 current-side changed lines. Two active files contain only
line deletions. The complementary pass scanned 136,392 current-side changed
lines across 398 paths. It parsed all 170 Python files in that scope and
inspected changed lines in the other 228 files. The literal and text filters
produced candidates for manual review.

Focused source review followed ownership and call sites across Core, CLI, MCP,
the updater, SQL migration, public packaging, tests and CI. The scans covered
product versions, one-off exceptions, path and repository assumptions, fixed
identifiers, policy duplication and time or size bounds. Manual checks traced
representative occurrences into their owning contract. A line's attribution is
the matching commit from `git blame` at the cutoff.

## Follow-ups

### P1 · Enforce the same-major policy for opaque versions

- `src/processforge_core/maintenance/versions.py:184–208,230–247,252–277`.
  The ordering comes from `815c0f9cdad8`. The major check is attributed to
  `74fd641aa0b2`. The updater passes the configured `allow_major` from
  `tools/processforge.py:15901–15919`.
- A direct call to `UpdateVersionSelectionPolicy.select_admissible` chose
  `1.1.0` over `2.0.0` with `1.0.0` installed and `allow_major=false`.
  With an opaque published label in place of `2.0.0`, it chose the opaque
  label and reported lexical ordering. The check covers release selection.
- Require a provable same major whenever the source forbids major changes.
  Continue the search for an eligible release. Test both an opaque candidate
  and an opaque installed version. Keep the legacy order for policies that
  allow it.

### P1 · Verify the Work owner when Director is disabled

- `src/processforge_core/project/coordination_state.py:202–221`
  (`c6c16eb7aa4d`) and `src/processforge_core/project/mode.py:26–35`
  (`8b141d26298f`)
  derive Forge from the organized project. MCP and CLI route from
  `coordination.director_enabled` in the workplace.
  See `tools/pf_runtime/mcp_bridge.py:45–53,203–211` (`691ede591f97`)
  and `tools/pf_cli/forge_work.py:19–29` (`fb412df69124`).
- The four combinations were checked through the project status service and the
  MCP route selector with a stubbed workplace configuration. The organized
  project with a disabled Director reported Forge and selected Garage. A simple
  project with an enabled Director reported Garage and selected Forge. The
  resulting Work write behavior requires a separate test.
- Exercise start and transition across the four combinations of project mode
  and Director availability. Assert one owner of each transition. For
  operations that require Forge, verify that refusal happens before any local
  write. Existing Forge connection failures already return on the Forge route.

### P2 · Bound the updater's wait for the replacement CLI

- `tools/pf_cli/core_update_lifecycle.py:111–137` (`85a59b6005ff`)
  gives the child `runtime start` a timeout argument. The enclosing
  `subprocess.run` has an unbounded wait.
- A hang before the child handles that argument could leave the updater waiting
  after Core has already been replaced. Source inspection establishes the
  missing outer bound. A hang was outside the executed probes.
- Apply an outer budget derived from the existing timeout. Handle
  `TimeoutExpired` within the existing verification result, while keeping
  evidence that the file apply completed. Test a child that never returns.

### P2 · Derive onboarding event identity from the selected process

- `tools/processforge.py:3102–3134` (`bdb29c611cd1`, `276ad5cd2cfa2`)
  repeats the process ID and version across eight emitted events. Today the
  literals agree with `processes/core/project-onboarding.yaml:6`.
- Resolve those values once from the selected definition or bind the shared
  constants to it with a parity test. Verify all emitted identities and that
  event paths refer to the generated records.

### P2 · Take the CI artifact repository from the current run

- `.github/workflows/public-core-upgrade.yml:145–147` (`f01bfc74931b2`)
  uses the current run ID and the official repository. The manual trigger at
  line 6 and official release download at lines 150–153 were introduced by
  `b78b8d7d0ad3`.
- Parsing the workflow and its embedded Python confirmed the current run ID is
  paired with a fixed repository. A dispatch in a fork with Actions enabled
  would query the official repository for its own candidate artifact.
- For the run artifact, use `GITHUB_REPOSITORY` and verify the dispatch
  scenario. Preserve the canonical repository for the published baseline.

### P2 · Take the target version from the selected release plan

- `docs/contributors/collaboration-profile.json:9`,
  `docs/contributors/task-collaboration.md:12` and
  `docs/ru/contributors/task-collaboration.md:14` (`9caf036531bd`) present
  `1.3.0` as the current target. The audited `VERSION:1` is `1.3.1`
  (`70cd03380164`), and the open milestone is 1.4.0.
- Contributors copying the profile can attach work to a stale release. The
  value is guidance in the shared profile. Use the selected release plan as
  the source of the target version and update both instructions together.
  Check that a contributor can derive the intended target for a new Work.

### P3 · Keep the two generic-shell definitions in sync

- `src/processforge_core/runtime/drivers.py:56–97` (`0a8b5029a1cf`)
  omits `command.model_args` recorded in
  `templates/runtime-drivers/generic-shell.yaml:11–13`. The command builder
  supplies the same arguments by default at
  `src/processforge_core/runtime/command.py:340–349` (`55b5cc5fe8c2`).
- Workplace generation and catalogue fallback can load different
  representations. The comparison of five driver definitions found a
  structural difference. Current effective argument values match. Add parity
  coverage or make both consumers load one verified definition.

### P3 · Link release-note packaging to the published inventory

- `src/processforge_core/maintenance/release_sources.py:42–55,110–125`
  (`fd477d350b56`, `7d7e33fa490f`, `b6c1d31b34ed`) lists 12
  historical paths. Current changelog links resolve to packaged notes.
- The list preserves a narrow release allowlist and carries manual drift risk.
  Verify linked release-note membership when qualifying the archive. Once the
  remaining notes reside under the documentation root, recheck archive parity
  before reducing the list.

### P3 · Share a test dependency pin across CI jobs

- The nine CI pins match `tools/python-qa/requirements.txt:3`
  (`c75c0f54c2c5`). See `.github/workflows/linux-native-execution.yml:31`
  (`297817488e33`), `.github/workflows/public-core-upgrade.yml:109`
  (`3c5687c06eb3`), `.github/workflows/storage-recovery.yml:31,113`
  (`23aff44e00ea`, `e1728b6efa98`) and
  `.github/workflows/repository-checks.yml:198,241,291,408,593`.
- An upgrade can leave jobs on different test-runner versions. Use a shared
  requirement or parity check that works on CI's Python 3.11. Check every job
  against that source when the pin changes.

## Literals with a current contract

| Contract | Representative attribution and evidence |
|---|---|
| Test fixture roots and version cases | `tests/execution_migration/test_compatibility.py:28–31` (`ca5109339195`) and `tests/work/test_compact_capsules.py:315–322` (`8b141d26298f`) require explicit fixture roots. `tests/update_versions/test_selection.py:20–32` (`815c0f9cdad8`) uses sample versions to verify ordering. All 13 table cases passed a direct policy check. |
| Runtime defaults and launchers | `templates/workplace-configuration.yaml:3–11` matches `PFConfig()`, the source used by `src/processforge_core/project/workplace_templates.py:308` (`811f3469dc43`). The existing smoke checks parity. `bin/pf.bat:2–9` and `bin/pf-server.bat:2–9` (`70c7e76ac7db`) choose an available interpreter and forward its exit code. |
| Updater compatibility | `src/processforge_core/maintenance/file_update.py:32–53,84–114` (`07b859e87a5a`, `37c305684265`). The legacy asset is qualified by released template, preimage and binding evidence. [Core update contract](../concepts/core-update-manifest.md) |
| Platform paths and permissions | `src/processforge_core/configuration/device.py:13–25` (`4c3e1272a11e`) resolves absolute platform bases. `src/processforge_core/maintenance/file_update.py:892,921` (`4ee7f44854ef`, `0ee3c165fae6`) bounds distinct update lock waits. Evaluate the combined budget if a caller promises an overall deadline. |
| Authority and SQL storage | `src/processforge_core/maintenance/first_write.py:41–57` (`6edcf2c29c92`, `7a4dccb0b8f1`) distinguishes a proven fresh project from an existing project requiring migration. `src/processforge_core/maintenance/execution_migration.py:49,184–214,1111` (`ca5109339195`) uses fixed plan IDs and versions in its validation and authority transfer. |
| Transport protocol | `tools/pf_runtime/loopback_http.py:11–53` (`30cdf249530b`) protects the loopback boundary. `tools/pf_runtime/mcp_bridge.py:186,252` (`f10dff1a152c`) fixes the JSON-RPC wire version. |
| Execution status | `src/processforge_core/executions/projection.py:17–31,128–164` (`276ad5cd2cfa`) owns public execution statuses and projection. Work, Runtime and SQL transitions each have their own authority. |
| Release fixtures | `tools/release_metadata_contract.py:11–17` fixes expected metadata for a specific release smoke check. `tools/install-contributor-knowledge.py:30–49,139–147` (`74121d7e1f1a`) restricts sources to the approved publication namespace and verifies the pinned archive. |

The Garage operator or the Forge updater owns lifecycle control. The existing
project first-write check returns `storage_migration_required` when its SQL
route is unavailable. The agent then requests the explicit migration action.
New project initialization uses its own receipt and SQL owner. Keep the writer
singular across the routing and recovery follow-ups.
[Architecture decision register](../architecture/README.md) ·
[Update guide](../getting-started/update-system.md)

## Separately reviewed PR

PR #180 was open at the cutoff. The early head `de7f1a4b6216db725b57acc864311fbf60d8dfdb` carried forward
ordinary POSIX permissions but could replace a live file before proving the new
owner could read it. The final candidate reviewed here is
`00c99d0a59fde89053d13226f59783f18d82453e`, tree `4903e693043ee14fc4356b1106b5c494aa28739d`. Its shared apply/resume writer reopens
the staging file after setting access bits and before replacement.
See `src/processforge_core/maintenance/file_update.py:212–231`.

Release archive SHA-256 `625c3a4345632dcc4e9e7f3b725f199ca3a14286466f965c40750f5f6e1dbabb` passed actual apply and same-ID recovery
from published 1.3.1 on Windows and Linux. Tests verified released manifest and
payload bytes, real launcher execution, Linux mode and umask behavior, and the
preimage after Linux refused to reopen the replacement under the updater's
identity. Windows exercised recovery from a native launcher sharing violation.

## Reproduce the inventory

Run the following in PowerShell from a checkout with both revisions. The
metadata pass counts deleted paths. The changed-line pass uses additions and
modifications and excludes the private state directory. Python counts
`ast.Constant` nodes that intersect the new-side intervals in the diff.

```powershell
git rev-parse 'v1.2.0^{commit}'
git merge-base --is-ancestor b70df739700f1559570f4b65481cd39616ccc1ea 03cd92913007df41a907bdd2d41fa6bc741c729a
@'
from collections import Counter
import subprocess

base = "b70df739700f1559570f4b65481cd39616ccc1ea"
head = "03cd92913007df41a907bdd2d41fa6bc741c729a"
common = ["--no-renames", "-z", base, head]

def diff(*options):
    return subprocess.check_output(["git", "diff", *options, *common])

fields = diff("--name-status").decode("utf-8").split("\0")
rows = dict(zip(fields[1::2], fields[::2]))
active = {path for path, status in rows.items() if status in {"A", "M"}}
product = {path for path in active if path.endswith(".py")
           and not path.startswith("tests/")}
support = active - product
changed = {}
for row in diff("--numstat").decode("utf-8").split("\0"):
    if row:
        added, _, path = row.split("\t", 2)
        if path in active and added != "-":
            changed[path] = int(added)
print(Counter(rows.values()))
print("Python outside tests:", len(product), sum(changed[p] for p in product))
print("Complementary paths:", len(support), sum(changed[p] for p in support))
print("Python in complementary paths:", sum(p.endswith(".py") for p in support))
'@ | python -B -
```

For changed lines use `git diff --diff-filter=AM --no-renames --no-color -U0
<baseline> <cutoff> -- . ':(exclude,top).pf/**'`. Apply the same lane selection
as in the metadata pass. Use `git blame --line-porcelain -L <start>,<end>
<cutoff> -- <path>` for an attribution. The text pass filters the
complementary scope for version strings, paths, branch and repository names,
permissions, fixed IDs and compatibility markers. Use matches as an index for
source review.
