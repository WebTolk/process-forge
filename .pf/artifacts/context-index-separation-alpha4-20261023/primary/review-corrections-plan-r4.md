# Correct all four final r13 review findings in a separate successor candidate

The completed native review-final reported CODE NO-GO with four reproduced
defects. Preserve its entire r13 candidate-batch tree, manifest, probes, reports,
native status and r3 QA packet unchanged. No product commit/push/tag exists yet.
Current primary/Core writer scopes remain valid and unchanged; these are further
corrections of source availability, metadata identity and coherent observation.

1. Resolve every declared enabled index root strictly for explicit collection;
   an unavailable root is a bounded document_scan_failed error, not an omitted
   resource. Readers retain their current non-building selection semantics.
2. A source read/scan failure discovered during file verification must not select
   destructive rebuild. Preserve the existing maintenance payload but return a
   failed pass without deleting prior DB. Explicit rebuild must collect/validate
   its sources before unlinking the old cache and reuse that captured material.
   The released explicit rebuild's replacement contract otherwise stays intact;
   no new schema, filesystem database swap or Runtime operation is introduced.
3. Bind each stored resource fingerprint to the complete canonical actual-root
   set in addition to its declared fingerprint, even for zero-document roots.
   Compare that identity in selected catalogue projection and explicit verified
   status. Keep logical root_ref and public query payloads unchanged; no new DB
   column/schema version or unselected body read. Older derived fingerprints can
   become stale and are reconciled only by explicit authorized maintenance.
4. Main's observe_search_index_for_project must capture a checkpoint around both
   physical observation and scoped coverage. A changed/unavailable identity yields
   a bounded degraded/unavailable row, cleared generation/counts, no retry/wait
   or indexing. Use a new clean-HEAD transform, preserving unrelated Main bytes.

Add red/green regressions for established-index root refusal/missing roots,
verified read failure and explicit rebuild preservation, empty/unselected root
remapping/addition, metadata-only collection and the real Main composed-read race.
Use a new candidate worktree and QA/review packet. Repeat affected/full registered
checks justified by these code changes and obtain a fresh independent native
review. The current rejected review is completed work, never product CODE GO.
