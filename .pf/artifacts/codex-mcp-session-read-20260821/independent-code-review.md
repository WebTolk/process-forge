# Independent code review

Reviewer: independent code reviewer, 2026-08-21.

Accepted findings corrected before final validation:

- added `session_mismatch` guard and negative smoke for process-bound MCP;
- installer now writes both `command` and `commandWindows`, limits SessionEnd
  to three seconds, and configures other observation handlers async;
- added documented `SessionStart: clear` mapping and proof;
- debug output is stderr-only, preserving one hook-protocol JSON value;
- backup names include microseconds; session read avoids stale-presence writes;
- raw replay now reconstructs conversation messages and has a regression smoke.

Residual non-blocking note: transcript and event files are read before their
bounded response pages are shaped. The response surfaces are capped, while a
future Core indexed reader can bound I/O for very large histories.
