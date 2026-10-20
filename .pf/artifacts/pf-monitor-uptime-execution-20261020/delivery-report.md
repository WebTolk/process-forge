# Source delivery readiness

Decision: ready for the explicitly authorized one-task source delivery in `dev`.
Complete source assurance passed; see `test-report.md`, `code-quality-report.md`,
and the sealed hashes in `checks/source-manifest.json`. The original planning
card is now `done` through native `task-complete --apply`; its old planning-only
scope was not widened, and all other backlog task records remained unchanged.
The backlog Run remains `draft`.

Delivery profile decision: installed-device and public-release delivery are
skipped with reason. The user narrowed this execution to one task, commit/push
both remotes, then stop. This Work does not authorize a new alpha publication,
installation, host restart, or final ZIP content acceptance. Canonical source
release tests built two untracked candidate artifacts as part of their normal
test execution; they are retained privately and are not promoted to a release.

The remaining source transport is authorized and concrete: create one commit
from accepted `dev` parent `7a4021788643e5df325f5ac1e1df1ab70ed02ac6`, containing
only this task's sealed source delta, native Work closure, original card closure,
and owned artifacts/log/handoff. Preserve unrelated working-tree and index data.
Use the isolated index helper; construct shared metadata commit content from
accepted HEAD plus only this card's change. Push that commit to `origin/dev`
and `gitverse/dev`, then read both refs back and require the exact local SHA.
GitVerse uses the existing environment token via askpass with credential helper
disabled; no credential is placed in command arguments or public files.

This stage records source readiness and the explicit profile decision. It does
not claim an already performed push. Actual commit/readback results are retained
in task-private `git-delivery.json` and reported after transport. Native final
Work/task doctors and the final delivery receipt are the completion checks.
After that delivery, stop; do not start another backlog implementation.
