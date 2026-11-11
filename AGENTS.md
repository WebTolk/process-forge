# Working on ProcessForge

These are mandatory repository instructions for every coding agent. Read
[CONTRIBUTING.md](CONTRIBUTING.md) before changing files; the Russian edition is
[CONTRIBUTING.ru.md](CONTRIBUTING.ru.md). Apply this workflow across sessions and
devices without asking the user to repeat it.

For a new device, follow [contributor agent setup](docs/contributors/agent-setup.md)
([Russian](docs/ru/contributors/agent-setup.md)) for the shared knowledge profile,
verified package installation, Python QA and MCP configuration. Use the pinned
packages in `docs/contributors/knowledge-packages.json`; load their indexes first
and only the documents relevant to the task. PF-specific contracts remain in the
current source revision. A clone supplies shared instructions; initialize your
own ignored `.pf` state before substantive governed work.

- Use local PF for substantive development: resolve a valid project context,
  create or resume the exact Work, read its assignment/capsule and obligations,
  and follow its stages through verified completion. Initial reading, environment
  setup and repair of the startup instructions may precede a Work. Use the
  installed CLI if MCP is unavailable; start only services required by the chosen
  process. Do not reconstruct another developer's private history.
- Follow [task collaboration](docs/contributors/task-collaboration.md)
  ([Russian](docs/ru/contributors/task-collaboration.md)). The shared default in
  `docs/contributors/collaboration-profile.json` is `local_pf`: local PF owns task
  accounting and GitHub mirrors substantial tasks/results. An issue is not a
  prerequisite in this mode. In explicitly selected `github` mode, read or create
  the issue before starting the corresponding Work; GitHub owns the shared task.
- Read supplemental `project.collaboration` and Work `collaboration` fields from
  the selected local manifest/assignment, even if the compact PF response omits
  them. They hold the repository/integration branch and issue/working branch/PR
  URLs. Several Work may reference one issue. Links do not change the task source,
  widen a capsule's permissions or authorize closing an unfinished shared task.

- GitHub is the primary place for code review and accepted source delivery.
  Task authority follows the selected collaboration mode.
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
- The root project `.pf/` is private local state and is never tracked or packaged.
  A fresh clone must be bootstrappable without pre-existing `.pf` history. Create
  your own local state from shared instructions and preserve it on subsequent
  runs. Product templates and isolated consumer fixtures remain supported.
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
  branches. Publish issue summaries according to the selected task mode and
  authorized scope; no automatic issue synchronizer is assumed.

More specific `AGENTS.md` files refine source organization and validation; they
do not replace this contribution workflow. User instructions take precedence.
