# Git source qualification

The second complete public source attempt passed the repaired checksum gate
and 245 checks, then stopped at `smoke_release_manifest_provenance_contract`.
Its release-pack operation requires a clean source commit; the isolated
candidate had the correct source bytes staged but not committed. This is a
qualification setup failure, not a product regression. The failed attempt is
retained task-private as `attempt-2`.

Create a detached local qualification commit containing exactly the five sealed
source/test/docs/inventory paths. Verify that its Git worktree is clean and that
the main `dev` head is unchanged. Run the failed native smoke first, then rerun
the complete canonical source suite and supervisor-stress on that clean source
commit. No source bytes change for this qualification, and no branch or archive
is published from the candidate.
