# Agent entry contract and explicit migration

The canonical startup contract K is `templates/agent-entry-contract.md`.
Its metadata fixes the contract version, SHA256 of UTF-8 LF bytes, the 4096-byte
ceiling including markers, and reviewed legacy prefix hashes. Contract version,
manifest schema version and Core release version are separate identities.
`agent_entry.py` validates the source and renders the full K directly in root
`AGENTS.md` and hidden `.pf/AGENTS.md`. The hidden form adds extended instructions.
`templates/project-agents-template.md` is a checked derivative; an independently
edited K there is an error. K changes require a new contract version and review
of all eight clauses; a matching hash alone is not semantic review.

## Commands

For existing Work, use the [continuation protocol](work-continuation.md) with
exact run, assignment and context selectors. Rewording an objective in
`work-start` can create another Work and must not serve as a resume operation.

```text
pf agent-entry plan --project-root <project>
pf agent-entry check --project-root <project>
pf agent-entry plan --project-root <project> --budget-file <policies.json>
pf agent-entry apply --project-root <project> --plan-file <reviewed-plan.json> --apply
pf agent-entry rollback --project-root <project> --transaction <transaction-id> --apply
```

Every command prints JSON. Save a plan's exact JSON as UTF-8 without BOM using
your caller's output capture, review it, then pass that file to `apply`.
Plan/check do not create files, diagnostics, locks, Runtime or sessions. Apply and
rollback require the explicit `--apply` flag. There is no force option.
The entry transaction changes only `AGENTS.md`, `.pf/AGENTS.md` and
`.pf/agent-entry.json`. Initialization and deterministic restoration use this
same service before ordinary project writes. Prompt modernization and
client-specific adapters remain separate integrations.

## Initialization and repair

`init-project`, `project-init` and `project-onboard` preview an entry plan and,
with `--apply`, create full K in root and hidden instructions. Existing root
text and recognized legacy hidden suffixes retain their bytes. Entry targets
never pass through the generic force writer; `--force` cannot bypass their
ownership or budget checks. `START_AGENT_HERE.md` is no longer needed and is
not generated in new projects. Existing START files remain untouched, including
during forced onboarding and deterministic repair. A missing START is normal:
it does not affect initialization status or doctor and is never restored by repair.

`project-init-status` exposes `agent_entry` separately from `snapshot` and
project `state`. A missing root/entry manifest can be `legacy_or_unmigrated`
while the context stays fresh and the project stays complete. Unknown hidden
instructions report an entry conflict. Status never migrates the project.

```text
pf project-init-repair --project-root <project> --repair-action migrate_agent_entry
pf project-init-repair --project-root <project> --repair-action migrate_agent_entry --apply
pf project-init --project-root <project> --workplace <workplace> --entry-budget-file <policies.json> --apply
```

The explicit `migrate_agent_entry` repair touches only the entry transaction;
it does not refresh snapshots, rewrite capsules, update START, or run onboarding.
Repeating a current entry repair is read-only. `restore_deterministic_artifacts`
also preflights entry ownership before its existing deterministic repair work.
Both actions accept `--entry-budget-file` with the generic JSON array described
below. MCP initialize/repair accepts that array as `entry_budget_policy` and uses
the same service, existing Ledger binding and exact `apply: true` requirement.
No effective client settings are inferred when the array is absent.

Known conflicts or truncation stop initialization before ordinary flow files or
events are written. An interrupted entry transaction returns `status: blocked`
and its recovery receipt; ordinary initialization does not proceed. For an
acknowledged new project whose root does not exist, the validated root directory
must be created first so the entry plan can bind its identity. Dry-run still
requires an existing root. General onboarding is not an atomic transaction: if
a later doctor or ordinary initializer step fails, the completed entry receipt
remains in private journals for explicit diagnosis/rollback.

## Ownership and preconditions

A new root receives K; an existing root without markers retains every original
byte and receives an explicit trailing separator and K. Known managed blocks
are recognized by version and full normalized hash. Surrounding UTF-8 bytes,
BOM and line endings remain unchanged. A current CRLF block stays unchanged.
A known legacy hidden prefix can be replaced while retaining its exact extended
suffix. Unknown customized hidden instructions need reconciliation.

Duplicate, nested or malformed markers, an unknown version or modified owned
text produce a conflict. Encoding is never guessed. Redirected/reparse paths,
hard links, special files, case collisions, read-only targets and unsupported
permissions block the operation. Target text is bounded to 1 MiB per file.
The public manifest owns the two projections' contract identity, not arbitrary
surrounding user text. Unknown schemas and additional manifest fields conflict.

Plans bind the project identity, canonical source/template metadata, target
preimages, file identity and permissions, and selected budget inputs. Apply
checks the entire reviewed plan again under an OS-held writer lock. A changed
source, input, target or plan is rejected. Public reports contain generated K,
hashes, sizes and K offsets, without existing user text or absolute paths.
Adding K does not prove the absence of semantic conflicts with user instructions.

## Instruction accounting

Without effective budget observations, the result is `budget_unverified`.
File generation can proceed, but it does not establish client readiness.
An explicit generic policy file is a JSON array, for example:

```json
[{
  "id": "operator-observed-chain",
  "unit": "utf8_bytes",
  "scope": "chain",
  "selection": ["AGENTS.md", "nested/instructions.md"],
  "limit": 24000,
  "overflow": "truncate",
  "source": "explicit",
  "accounting_phase": "raw_concat"
}]
```

This is an example observation, not a client default. All selected files are
required. Their order and duplicates count; unselected files do not count.
The service counts the whole proposed files, including user text and BOM,
and reports K's byte offsets separately. `file` scope limits each selected file;
`chain` uses the ordered sum. Units are `utf8_bytes`, Unicode `unicode_scalars`,
`utf16_code_units`, or `tokens`. Tokens have no generic tokenizer here and stay
unverified. Unknown limits (`null`), unknown accounting, and `default`/`unknown`
sources do not establish effective host configuration. `accounted` means only
that the supplied raw-concatenation policy was measured, never host certification.

Known `truncate`/`reject` loss of K or any required text blocks apply, even when
K itself fits. `warn` preserves delivery in this accounting model and emits a
warning. No automatic shortening, relocation or global budget increase occurs.
Client selection, imports, wrappers, trust and effective host settings require
their own adapter and delivery evidence. A raw-concatenation observation cannot
represent unmeasured expansion or wrappers. Model token context is separate.

## Transactions and recovery

The OS releases the writer lock when its process exits; the lock file is retained
to avoid splitting locks across inodes. Private preimages and receipts live in
`.pf/runtime/agent-entry-transactions/`; staging lives in `.pf/tmp/agent-entry-*`.
These retained directories are recovery evidence and may contain private user
text. Do not publish them. The journal has bounded, integrity-checked data and
fixed target paths; it is local-owner recovery storage, not an adversarially
signed artifact. The inventory is bounded to 256 journals; retention is explicit.

Each data replacement is atomic. The transaction across files is not atomic.
The manifest is written last, then all files are verified before commit. On
Windows, owner/group/DACL preservation is preflighted on empty isolated files;
data replacement and ACL restoration are separate journaled steps. New files
use the current owner's private staging permissions. On POSIX, existing mode
bits are retained; other owners/groups and extended access ACLs are unsupported.
A permission failure never enables an ignore-ACL fallback.

Interrupted transactions remain pending, including a crash just after manifest
replacement. Apply returns `incomplete` when it can report the interruption;
after process death, plan/check find the pending journal. Explicit rollback is
the recovery operation. It compares all current files and expected permissions
before restoring anything, handles known intermediate ACL states, restores exact
preimages and removes only unchanged files created by that transaction. Later
edits cause `rollback_conflict`; repeating a completed rollback is read-only.
No forward-resume or multi-file atomicity is claimed. The lock coordinates PF
writers and is not a sandbox against a hostile concurrent filesystem owner.

## Compatibility startup prompt

`agent-start-prompt --project-root <project-root>` only prints current guidance.
It does not read a stored START as execution authority, choose a Run, or write
project files. Its output is independent of zero, one or multiple active Runs. Ordinary work follows `pf.work.start`,
`pf.work.state` and `pf.work.transition`; compatibility Run/Task commands remain
available for their explicit diagnostic uses.

For explicit legacy compatibility only, use `--plan` to inspect the JSON
placement plan and `--apply` for a START-only transaction. Onboarding and repair
never invoke this optional placement. Only exact recognized previous generators may be
replaced; customized text conflicts. Existing current text retains its raw
BOM/CRLF bytes on no-op. A recognized legacy replacement preserves its BOM and
uses current LF text. The shared entry lock, preconditions, source fingerprint,
ACL/path checks and rollback journal apply. START placement never changes
AGENTS, its manifest or snapshots, and makes no native instruction-budget claim.
Recover with the existing `agent-entry rollback` operation and returned
transaction id. Use the generating or newer Core for recovery: older Core
cannot read START-only journals. Roll back before downgrading.

New context source records prefer root `AGENTS.md`; a project without it keeps
an explicit legacy hidden-entry fallback. Extended hidden instructions are
available on demand. Newly generated snapshots record the returned Work and
resource-selection path; their Markdown renders that recorded read order.
Existing snapshots and capsules are never rewritten by preview or placement.

## Qualification

### Read-only profile diagnostics

`agent-entry profiles` lists the versioned registry. `agent-entry diagnose
--project-root <project-root> --profile P-CODEX --cwd subdir` inspects actual
files without planning replacements. `--cwd` is relative to the supplied root;
the default is `.`. Existing `agent-entry check` retains its migration-plan
semantics. Neither operation starts infrastructure or changes client settings.

Diagnosis returns separate `file_consistency`, `discovery`, `delivery`,
`behavior`, `enforcement` and `runtime_context` verdicts. Only complete current
file projections and manifest identity can be `verified` here. Discovery is at
most `conditional`; actual delivery and behavior require native evidence.
Enforcement is `not_applicable` to this filesystem diagnostic. Exit code 1 means
a concrete blocker or invalid input; exit code 0 can still contain `unverified`
verdicts and is not a compatibility certificate.

Optional `--observations-file <file>` accepts a bounded version-1 JSON object
described by [the diagnostic schema](../../schemas/agent-entry-diagnostics.schema.json).
For a conditional Codex prediction, supply `profile_version` and `client_revision`
from the registry, `settings_source: "explicit"`, `injection: "enabled"`,
`trusted: true`, `boundary_complete: true`, `single_environment: true`, the
observed `root_markers`, `fallback_names`, and numeric `limit`. These values
are caller observations, not authenticated host facts. Missing values remain
unknown; global configuration is never scanned. A changed client revision does
not inherit the pinned profile's qualification.

The Codex source model selects one file per directory from the nearest observed
marker to cwd, with override before AGENTS even for an empty override. Without
a marker it considers cwd only. The supplied project root bounds all reads;
outside ancestors or multiple environments require separate qualification.
The measured budget uses selected UTF-8 bytes, including BOM/CRLF, and the
loader's whitespace-only rule. K completeness and completeness of all required
instructions are separate. Defaults are estimates; unknown settings, accounting
or coverage yield `budget_unverified`. Unsafe or unsupported paths are a
limitation of this diagnostic, not evidence that a native client rejects them.

Other registry profiles describe explicit product surfaces and prerequisites.
Their optional `selection` is an observed ordered list of project-relative
inputs, not automatic import expansion. Kimi's pinned profile deduplicates the
same path and reports a conservative trimmed-content lower bound for its
warning-only rendered budget; wrappers and actual expanded size stay unknown.
OpenClaw reports raw UTF-16 per-file and aggregate counters independently,
with separate limit provenance. These counters cannot certify bootstrap
wrappers, truncation or K delivery. Workspace, injection and context mode must
be observed separately; `skipBootstrap` is not an injection-disable setting.
Explicit adapter placement is described below; native client qualification remains separate.

Optional `context` observations distinguish fresh/nonblocking-warn, stale,
broken, identity mismatch, denied resources and unavailable MCP/CLI. Verified
existing CLI observations can describe a conditional fallback; diagnosis does
not validate freshness merely because a snapshot file exists. Unknown context
stays unverified. Reports contain hashes, counts, relative paths and fixed
reason codes, not instruction text or configuration secrets.

Run `python -B tools/smoke_agent_entry_profiles.py` for paired source fixtures,
strict observation/schema validation and CLI byte/mtime invariance.

### Profile evidence

Registry sources describe the research snapshot dated 2026-09-28, not a blanket
claim about current client versions. Source-backed rows carry immutable commits.
The documentation-only Copilot CLI row refers to its
[instruction locations and combinations](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions).
The Cascade row refers specifically to the
[Devin Desktop instruction surface](https://docs.devin.ai/desktop/cascade/agents-md).
Neither row certifies a binary or model session. Native-client qualification
requires a new version/settings/platform tuple and actual delivery evidence.

Run `python -B tools/smoke_agent_entry.py` for source, renderer, ownership,
instruction accounting, Windows ACL/path cases, injected interruptions, real
process death, OS lock contention and CLI read-only behavior. POSIX behavior
requires a separate run on that platform. These tests do not certify native
client discovery, delivered prompts, model behavior, installed Core or connected
MCP. See [Work context](work-context.md) for creation-only scoped Work input.
Run `python -B tools/smoke_project_init_entry.py` for initialization, legacy
status, explicit repair, preservation, no-write refusals and the source stdio
MCP adapter. This is not a connected application-host acceptance test.
Run `python -B tools/smoke_agent_start_prompt.py` for preview invariance,
recognized placement, conflict/recovery and new/legacy context-reference cases.

## Explicit client adapters

Choose one route explicitly. `adapter-plan` is read-only and requires current
root/hidden K and entry manifest; migrate entry separately if they are missing.
Only Claude and Gemini `native-import` routes can write a vendor file:

Save the printed adapter-plan JSON as UTF-8 without BOM in `adapter-plan.json`,
review it, then run adapter-apply with that file.

```sh
pf agent-entry adapter-plan --project-root . --profile P-CLAUDE --route native-import
pf agent-entry adapter-apply --project-root . --plan-file adapter-plan.json --apply
pf agent-entry rollback --project-root . --transaction <receipt-id> --apply
```

Use `P-GEMINI` for the Gemini route. Claude's section imports `@AGENTS.md`;
Gemini's imports `@./AGENTS.md`. The plan shows the exact generated section,
target and hashes. Only the selected vendor file changes. A new section is
placed at the beginning, after an existing BOM, to avoid a trailing unclosed
code fence. All original bytes remain after it. Existing exact managed sections
are idempotent, including CRLF. Edited, duplicate or misplaced markers conflict.
An unmanaged import-like AGENTS reference also conflicts conservatively, even
inside a code example; this duplicate-risk check is not a native Markdown parser.
PF neither adopts nor deletes user imports. Review such a file separately.

Apply rechecks the plan, source and entry/budget input hashes under the existing
entry lock. Journals and rollback use the same fixed-target transaction service.
An interrupted transaction blocks further placement until explicit rollback;
later user edits can block rollback. No host configuration is changed.

```sh
pf agent-entry adapter-guide --project-root . --profile P-AIDER --route explicit-read --cwd subdir
pf agent-entry adapter-guide --project-root . --profile P-CODEX --route root-agents
pf agent-entry adapter-guide --project-root . --profile P-OPENCLAW-EMBEDDED --route prerequisites
```

Guidance never writes or launches a client. Aider gets an argv array such as
`["aider", "--read", "../AGENTS.md"]`, relative to the reported project-relative
cwd; use it from that directory. PF does not claim automatic AGENTS discovery.
Native root profiles need no vendor file. Claude/Gemini also accept a
`root-agents` guide for an independently configured native route; this never
changes mode or `context.fileName`. A detectable existing vendor import conflicts
with that route. Unknown host settings cannot establish route exclusivity.
OpenClaw reports observed workspace/mode/injection prerequisites and never
creates or rebinds a workspace. Native harness and embedded profiles stay separate.

The plan counts whole vendor/root bytes and shows a **single-import preview**
with K offsets. It does not recursively expand user imports or reproduce native
wrappers. `expanded_bytes`, contract completeness and required-instruction
completeness remain unknown. Optional `--budget-file` uses the existing generic
raw accounting policies, under `budget.raw_policy`; a known raw truncation blocks
apply, but even an accounted raw policy cannot certify an expanded client budget.
Plan/guide delivery and behavior remain `unverified` after successful placement.

[Adapter report schema](../../schemas/agent-entry-adapters.schema.json) covers
plan and guide output. Run `python -B tools/smoke_agent_entry_adapters.py` for
source placement, preservation, budgets, fault recovery, rollback and CLI probes.
Native parser, installed client and model traces require separate qualification.
Import/read syntax follows the official [Claude memory documentation](https://code.claude.com/docs/en/memory#import-additional-files),
[Gemini import documentation](https://geminicli.com/docs/reference/memport/) and
[Aider read option](https://aider.chat/docs/config/options.html#read-file).

## Compatibility and support policy

For new or explicitly migrated projects, root `AGENTS.md` is the complete
minimum contract K; `.pf/` remains the state root and hidden instructions add
extended context. Neither K nor a current startup prompt sends the agent back
to START for authority. `agent-start-prompt` without `--apply` is a no-write
preview (`--plan` prints its placement plan). Stored legacy START may remain;
it does not choose a Run, require `first-assignment`, or override live context.
Legacy entry migration is explicit, separate from snapshot health, and never
rewrites existing capsules. Run/Task/session APIs remain available for explicit
compatibility and operator diagnostics; no Work or `process_choice_required`
is not permission to bypass the declared process with low-level commands.

Profile evidence has four levels, which must be reported separately:

| Level | Evidence | What it establishes |
| --- | --- | --- |
| D | Documentation for a named product surface | Described behavior, not an observed installation |
| S | Source at a pinned revision | Behavior visible in that source |
| M | Reproducible module/adapter probe | The tested implementation and fixture boundaries |
| E | Actual installed-client first-request trace | Delivery for that version, settings, platform and route tuple |

A registry row is not blanket support for every release, mode or editor feature.
Delivery evidence must show what reached the real client; a pointer file, printed
prompt, model's assertion, module smoke or profile exit code cannot replace it.
Behavior needs its own observation. T07 enforcement is claimed only for an
explicitly supported host route that actually enforces it, never from instruction
files alone. Unknown effective settings remain `unverified`.

The 4096-byte K ceiling is an internal contract constraint, not a per-file or
aggregate client budget guarantee. Raw selected bytes, expanded imports,
wrappers and all required instructions need their own accounting. Source tests,
release archive, installed Core and connected host are separate acceptance
boundaries. Use [flow layout](project-flow-root.md),
[entry order](session-bootstrap.md), and [global hints](global-agent-section.md)
without installing or repairing infrastructure during ordinary work.
