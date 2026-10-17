# Executed operator action

Existing Runtime restarted with the installed managed CLI after explicit --force approval. Command exit 0, old PID 13540 and launcher 9308 exited; new PID 16976 / instance 7e99504388824711a0e0c38b5fa400cf responds ready. Connected MCP PID 5284 was not restarted.

Only private evidence, reports/log and sampling scratch were directly written. No product writes, capsule edits, Core update/install, journal migration, host-hook changes, unrelated process termination or lock-file removal. The source-only SQLite implementation is not installed by this operator action.

Changed/evidence files: force-authorization.md, force-restart-command.json, new-owner.json, startup-cpu.json, settled-cpu.json, after-state.json, installed-provenance.json, cpu-summary.json, retained sample_cpu.py, report.md and the append-only task log. Earlier baseline/refusal evidence is retained.

Measured device CPU: before 21.8876% over 30 seconds; initial measured post-start window 21.4189% over 30 seconds; following 60 seconds 20.7354%, max 26.9430%. This operator objective is executed; next stage verifies recorded identities and arithmetic, without introducing product tests.
