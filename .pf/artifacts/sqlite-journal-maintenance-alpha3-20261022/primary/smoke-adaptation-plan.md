# Preserve the migration smoke after moving the application owner

The existing migration smoke imports the temporary migration script, calls its
public migrate entrypoint and patches private script symbols RawHookJournal and
_rows to inject interruption and source drift. The new script is a thin adapter;
the corresponding operations now belong to Core's JournalMaintenanceService,
RawHookJournal and JournalScanService.

Make one primary-owned, disjoint test contribution for the existing smoke file.
Keep its functional assertions: dry-run/refusal, explicit skipping, exact original
records and source bytes, idempotent repeat, interrupted barrier/recovery, source
drift rejection and identity-conflict rejection. Change injection locations to
the actual new owners, without adding compatibility machinery to production only
to support old private monkeypatch targets. No product scope or public CLI change.
Use the frozen maintenance architecture and actual resulting owners. Run the
adapted smoke and the new integrated tests; record exact results. The primary
owns registered QA; no new agent or executor responsibility is introduced.
