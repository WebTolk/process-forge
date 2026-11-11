# Contributing to ProcessForge

[Русская версия](CONTRIBUTING.ru.md)

These rules apply to people and coding agents developing ProcessForge itself.
GitHub hosts accepted source, pull requests and review. Task authority follows
[the collaboration mode](docs/contributors/task-collaboration.md): local PF is
primary by default for 1.3.0, with GitHub mirroring substantial tasks and results;
in explicitly selected `github` mode an issue precedes its local Work. GitVerse
mirrors accepted source. No automatic issue synchronizer is assumed.

## Starting from a fresh clone

Read root `AGENTS.md` and this guide before starting a task. No previous chat,
inherited `.pf` history or running PF service is needed to read/setup the clone.
Initialize your own local PF before substantive development. Inspect the branch,
working tree and `git remote -v`, then prepare a working branch from current
`origin/dev` as described below, even if the checkout initially opened `main`.

The canonical remotes are:

| Remote | Repository |
| --- | --- |
| `origin` | `https://github.com/WebTolk/process-forge.git` |
| `gitverse` | `https://gitverse.ru/webtolk/process-forge.git` |

A fresh GitHub clone already has `origin`. If `gitverse` is absent, add it:

```sh
git remote add gitverse https://gitverse.ru/webtolk/process-forge.git
```

If the clone came from GitVerse and its only remote is `origin`, rename that
remote to `gitverse`, then add GitHub as `origin`. Inspect existing remote
configuration before changing it; do not overwrite a different setup blindly.
Reuse available GitHub credentials and GitVerse token authentication. Keep tokens
out of remote URLs, command arguments, logs and files. Missing credentials block
remote delivery, not local analysis; report the specific missing access.

## Branches and delivery

`dev` is the integration branch. `main` is the release branch. Ordinary changes
target `dev` through a PR; do not commit or push task changes directly to either.
Choose a working branch that fits the work:

| Branch | Suitable use |
| --- | --- |
| `fix/<topic>`, `docs/<topic>`, `chore/<topic>` | One focused task or correction. |
| `feat/<topic>` | A feature developed through one or several coherent PRs. |
| `work/<developer-or-agent>` | An ongoing development branch, regularly synchronized with `dev`. |

Names are conventions, not mandatory identifiers. Include an existing issue number
when useful. In `local_pf`, a local task or accepted maintainer request can start
Work without an issue. In `github`, read/create the issue and bind its URL before
starting the Work. Several Work/iterations and PRs may address one issue. Store
links in supplemental project/Work fields as described in the collaboration guide.

The required route is **working branch -> checks -> commit -> push -> PR into
`dev` -> review and CI -> merge**. An implementation request includes this route
unless the requester sets a narrower boundary, such as a proposal or local patch.
Agents must not ask the requester to repeat this project policy for every task.

1. Read the request and applicable documentation. Inspect Git state and current
   remote refs. Define a bounded result and preserve unrelated local work.
2. Create a branch from current `origin/dev`, or synchronize an existing branch:

   ```sh
   git fetch origin
   git switch -c fix/example origin/dev
   ```

   On a long-lived developer branch, `git merge origin/dev` incorporates accepted
   changes without rewriting shared history. Coordinate ownership if others use
   the branch. Recheck affected behavior after resolving conflicts.
3. Implement the change and update its documentation. Keep unrelated cleanup out
   of the PR. Run applicable checks, stage explicit paths, inspect
   `git diff --cached`, then commit a coherent result with a meaningful message
   such as `fix: ...` or `docs: ...`. Several explanatory commits are fine.
4. Push the working branch to GitHub and create a PR with **base `dev`**. Link an
   issue when one exists. A developer branch can produce successive PRs; split
   independent changes when a cumulative diff would obscure their scope.
5. Address review findings and wait for applicable checks. Merge through the PR
   when authorized and required reviews are satisfied. Do not bypass failures or
   claim missing platform results as passes. If permissions or required review
   prevent completion, leave a reviewable PR and report the specific limitation.
6. Fetch the merged `dev`, mirror that exact commit to GitVerse, and read both
   remote refs back. Do not create a separate mirror commit or force-push shared
   branches. Keep branches needed for ongoing work.

Product promotion to `main`, tags and release artifacts follow the separate
[release procedure](docs/maintainers/release-publishing.md). An explicitly requested
contributor-instruction backport uses a separate reviewed PR to `main`; it must
not silently promote unfinished product changes or update release tags/channels.
After that merge, mirror and verify the resulting `main` ref as well.

## Setup and validation

For complete new-device preparation, use the [contributor agent setup guide](docs/contributors/agent-setup.md).
It defines the shared, independently released Python knowledge packages, initial
installation with pinned hashes, toolchains, MCP connections and readiness checks.
The [Russian guide](docs/ru/contributors/agent-setup.md) covers the same setup.

Use Python 3.11+ and an isolated environment with `requirements.txt`. Development
tools belong in a separate QA environment or an existing registered toolchain;
they are not runtime dependencies. The [Python QA bundle](tools/python-qa/README.md)
documents setup and lint, format, typecheck and test commands. Repository Ruff and
mypy configuration takes precedence over fallback configuration.

Run the public source checks from a clean checkout without project `.pf` state:

```sh
python tools/validate-process-forge-schemas.py
python tools/validate-process-forge-checksums.py
python tools/validate-public-cleanliness.py
```

After changing shipped files, run
`python tools/validate-process-forge-checksums.py --write`, inspect the inventory
diff and run its checker again. Run meaningful existing tests and smoke checks
for the changed behavior. Python changes require scoped Ruff lint/format and mypy;
distinguish unchanged baseline diagnostics from new failures. Whole-repository
formatting or technical-debt cleanup is not an implicit part of a focused change.

Executable changes require applicable checks on real Windows and Linux, including
affected file, SQL or process-lifecycle behavior. Native environments and CI runners
qualify. Missing backends, platform impersonation and `skip`/`xfail` do not satisfy
required scenarios. For documentation-only changes, explain why execution tests
are not applicable. Preserve useful failed results and corrected reruns, and record
the revision that each result actually checked.

## Pull requests and review

Explain the problem and resulting behavior first. Include scope, meaningful
commands/results, compatibility implications and remaining limitations. Link
issues, design decisions and durable evidence rather than private transcripts.
Review applies to the final change; rerun affected checks after subsequent edits.
A successful automation job is not itself a reviewer verdict.

AI-assisted contributions have the same correctness and review requirements as
other contributions. Authors must understand the change, verify generated output
and resolve actionable findings. Independent reviewers cannot present their own
implementation as independently reviewed.

## Repository hygiene and parallel work

The root `.pf/` belongs to the local environment. Never track or package its tasks,
run history, contexts, logs, credentials, caches or temporary data. An existing
local directory may remain; a contributor must not need someone else's private
state to build, test or understand this repository.

When updating an older checkout that still tracks `.pf/`, first preserve the entire
directory in a private backup outside that checkout. Git can delete unchanged
tracked files when applying the removal commit; `.gitignore` does not prevent
that. Restore any needed local state after updating and keep it ignored. A fresh
clone starts without `.pf/`; existing Git history is not rewritten by this change.

Reusable product templates belong in `templates/`, public examples in `examples/`,
regression fixtures with tests, and lasting explanations in `docs/`. Product and
consumer-fixture references to `.pf` remain valid; they do not authorize tracking
this repository's root project state.

Give independent writers separate checkouts and clear ownership. Synchronize code
through branches and PRs, and shared task decisions through GitHub. Preserve local
history and needed evidence before cleanup. Live databases and process receipts
are not a shared task queue to merge with Git. Never commit machine-specific paths,
tokens, environment files or raw private logs. Remove your disposable scratch
after preserving materials still needed for review or continuation.

Agents also follow [AGENTS.md](AGENTS.md) and applicable nested instructions.
Local PF context and Work govern substantive development after bootstrap.
Runtime, MCP, Agent Ledger and hooks are enabled only when the selected process
requires them; native CLI is a supported entry. Shared instructions and initial
setup remain usable before a Work exists.
