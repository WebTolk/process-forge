# ProcessForge device update — 2026-08-31

- Timestamp: 2026-08-31T06:17:00Z
- Agent/role: Codex primary agent
- Scope: manually replace the installed 1.1.0 prerelease Core with the final 1.1.0 archive, restart the scheduled Runtime, and verify the Codex MCP surface.
- Installed Core: `D:\.agents\processforge`
- Workplace: `D:\.agents\processforge-workplace`
- Release archive: `D:\Dev\process-forge\dist\processforge-1.1.0.zip`
- Full pre-update backup: `D:\.agents\backups\processforge-before-final-1.1.0-20260831T061513Z` (1,397 files, count matched the source)
- Updater backup: `D:\.agents\processforge\runtime\core-update\backups\core-update-20260831T061540Z`
- Update result: applied; 42 added, 221 changed, 1 removed, 646 unchanged, 0 locally modified, 0 missing owned.
- Installed validation: ProcessForge 1.1.0; 909 managed files; no incomplete update; checksum inventory PASS.
- Runtime: scheduled task `ProcessForge Runtime 5365635d5b5e` is Running; PID 12308; endpoint `http://127.0.0.1:60892`; TCP open; health ready; runtime doctor 8/8 PASS.
- MCP: Codex registration installed and enabled with no drift; direct JSON-RPC verification returned 13 tools, including `pf.context` and `pf.work.start`.
- Files changed: installed Core files under `D:\.agents\processforge`; this operation log only in the source checkout.
- Status: complete.
- Follow-up/residual risk: verify discovery and normal calls from a newly opened Codex session. Already-running Codex sessions can retain their old host-owned stdio MCP process until those sessions close.

## Console disconnect follow-up

- Timestamp: 2026-08-31T06:21:30Z
- Observation: the visible scheduled-task console printed `ConnectionAbortedError: [WinError 10053]` while a client disconnected after an `/event` payload had already been ingested and the server had begun its `200` response.
- Diagnosis: Runtime remained ready and scheduler jobs remained successful. The HTTP handler catches the response-write disconnect as a generic request error and attempts a second `400` response on the closed socket, which produces the console traceback.
- Device adjustment: replaced the task action's supported `--python` selection from `python.exe` to `C:\Users\musst\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe`; no installed release files were modified.
- Final runtime: task Running, `pythonw` PID 20708, no main window, endpoint `http://127.0.0.1:59382`, health ready, no scheduler error, runtime doctor 8/8 PASS.
- Final MCP recheck: 13 tools; `pf.context` and `pf.work.start` present.
- Residual product issue: aborted clients can still create `request.error` entries in `operator.log`; correcting that handler requires a separately authorized source fix and a new validated release artifact.
