# Focused behavior checks after implementation

`python -B tools/smoke_process_event_concurrency.py` exited 0 after the bounded append fix. Output: PASS: concurrent unique/duplicate Unicode events, prefix preservation, durable append, hook boundary and explicit lock failure. The same test had reproduced three duplicate ids before the fix (red-observation.md). Four actual independent Python writers now retain all 32 large Unicode events and one shared event, preserving all 512 seed records/bytes.

`python -B .pf/artifacts/event-journal-repair-20260926/repair.py --test` exited 0. Output: PASS: middle-fragment quarantine with 100 concurrent appends, byte/offset preservation, backup, wrong/multiple/tail rejection and drift abort. Tests operate in a temporary fixture, not the live journal. An unused overwritten EXPECTED assignment was then removed from the private helper; its active digest and test behavior are unchanged.

Live plan remains read-only: size 42978796 at observation; 35147 valid records, one invalid record at line 34212, offset 41877766, total 26 bytes including CRLF, 24-byte body with reviewed hash. Original history and active appenders remain untouched until release-delivery.
