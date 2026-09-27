# Handoff: installed T10 delivery -> remaining local follow-ups

Objective: update installed Core with the accepted monitor via standard PF updater.
Current status: actual installation and all post-install checks passed; consult the Run for final lifecycle completion.
Input artifacts: ../artifacts/t10-installed-delivery-20260926/delivery.md, assurance.md, build.json, install.json and exact command records.

Installed candidate 40c9894227738472976546849047550415099486. Update core-update-20260926T175155Z. Archive SHA256 79e666b2521309d45d0463ef46c4a5675e3aac8010cdd5adfe503291b48f7f0f. Backup D:\.agents\processforge\runtime\core-update\backups\core-update-20260926T175155Z. All 991 owned files, five backup files and protected/unowned files verified. No further apply of this same archive is needed.

Launch: `python -B D:/.agents/processforge/bin/pf.py monitor --workplace D:/.agents/processforge-workplace`. Add `--once --ascii` or `--json` for one snapshot. Runtime restarted with original port 0/interval 2.0; observed owner PID 11612, instance 078a3e69cf3e4ccbbf1adb6dab86a087. Re-read identity before any subsequent lifecycle action. Actual connected MCP process was not forcibly reloaded.

Files changed: only the nine accepted T10 product paths in isolated candidate and official installed owned payload; private delivery governance. Main source unchanged. Files not to touch: prior approved evidence/capsules; unrelated dirty work; configuration; unknown installed files; backup/control records. Scratch candidate/extracted trees retained as durable evidence.

Known issues: historical malformed .pf/runtime/events/events.ndjson line 34212, a 24-byte timestamp fragment plus newline; 35039 lines observed with exactly one invalid record before this update. Do not rewrite the active journal wholesale. Runtime warning for separately registered plg-content-varreplace is preexisting. Monitor cache over 1 MiB truthfully gives unknown counts; bounded authoritative metrics are next. No active count may be inferred from 96 historical cached session registrations.

Required checks passed: candidate 8 focused smokes + schemas/checksums/cleanliness, official release archive quick and extracted monitor, standard plan/apply/status, installed 3 smokes, monitor text/JSON, Runtime and Workplace doctor (known Runtime warning), hash preservation. Final Run doctor and nine-stage evidence are to be checked at closeout.

Next recommended action: close this delivery Work through actual run_completed, then start a bounded journal provenance/repair Work and local T10 activity-metrics/operator-interface Work. Preserve T07 design-only scope unless user includes its future engine; remote web remains deferred. Use standard Core updater for subsequent delivery too.

Final closeout: actual run_completed; assignment done; nine completed stages; run-doctor 21 PASS. See closeout.md and evolve-transition.json.
