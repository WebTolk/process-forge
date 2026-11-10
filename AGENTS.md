# Working on ProcessForge

These are mandatory repository instructions for every coding agent. Read
[CONTRIBUTING.md](CONTRIBUTING.md) before changing files; the Russian edition is
[CONTRIBUTING.ru.md](CONTRIBUTING.ru.md). Apply this workflow across sessions and
devices without asking the user to repeat it.

- GitHub is the primary place for code review and shared task coordination.
  `origin/dev` is the integration branch; GitVerse mirrors accepted source.
- Work on a task, feature, or developer branch. Long-lived developer branches
  are allowed and must be synchronized with `origin/dev` regularly. Keep each
  pull request understandable as a coherent change.
- The required delivery route is: working branch -> relevant checks -> commit
  -> push -> GitHub pull request targeting `dev` -> review/checks -> merge into
  `dev`. Do not commit or push task changes directly to `dev` or `main`.
  An instruction to implement a task includes this normal delivery route unless
  the user sets a narrower boundary. Honor repository permissions and required
  reviews; report the exact blocker if delivery cannot finish.
- Inspect Git state first. Preserve unrelated dirty/staged changes. Give parallel
  writers separate checkouts and non-overlapping ownership. Stage explicit paths
  and inspect the complete staged diff before committing.
- The root project `.pf/` is private local state and is never tracked, packaged,
  or required for contributing. A fresh clone must work without it. Do not create
  PF Work, start services, or reconstruct private history just to modify this
  repository. Product templates and isolated fixtures for PF-managed consumer
  projects remain supported and are distinct from this repository's own state.
- Use the shipped Python QA configuration and applicable repository checks.
  Preserve public contracts during refactoring. Test changed executable behavior
  on real Windows and Linux where applicable; an unavailable or skipped required
  scenario is not a pass. CI Linux runners are acceptable; WSL is not required.
- Report tested commands, exact revision, results and remaining limits. Keep
  useful prior failures alongside corrected runs. Starting a reviewer or receiving
  a successful tool exit does not itself prove semantic acceptance.
- After a permitted merge, mirror the resulting `dev` commit to `gitverse` and
  read both remote refs back. Use existing token credentials without putting them
  in URLs, command arguments, logs or committed files. Do not force-push shared
  branches. Issue mirroring is deferred and is not part of ordinary delivery.

More specific `AGENTS.md` files refine source organization and validation; they
do not replace this contribution workflow. User instructions take precedence.
