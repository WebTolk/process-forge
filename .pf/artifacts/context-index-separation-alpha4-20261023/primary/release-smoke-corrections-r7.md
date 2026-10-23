# Release-smoke acceptance correction

The full source qualification of commit 23ae166133390275a67ba92c1f00357bc757533a
failed after 165 successful checks at smoke_garage_no_hooks_sessionless. Its exact
report/trace/logs are retained under qualification/source-r1 and the portable
source-qualification-r1-failed.json. No tag/archive/publication was qualified.

The test assumes project context/search implicitly builds its fixture index.
That behavior is intentionally removed by the reviewed alpha4 contract. The
remaining-check diagnostic has independently reproduced the same assumption in
smoke_garage_session_enhanced and smoke_garage_cross_project_security.

Admit a bounded primary acceptance Work for these three smoke files only. Keep
every existing positive/search/pagination/security/session assertion. Each fixture
explicitly invokes the shared authorized workplace indexing CLI before positive
search assertions. The no-hooks fixture additionally proves fresh context and
pre-maintenance search do not create the database, then proves explicit maintenance
restores its original positive result. Bound its existing .codex cleanup to the
resolved fixture project before deletion.

No Core, Main, production CLI, storage or scheduler changes. The remaining-check
run is diagnostic only, never full qualification. Retain the original reviewed
r16 tree and source commit. A supplemental independently reviewed test-only
candidate and normal additional commit/push must precede a fresh full unfiltered
source gate and full exact extracted archive gate. Do not amend/rewrite the pushed
commit, reuse a rejected gate, weaken assertions, or publish diagnostic assets.
