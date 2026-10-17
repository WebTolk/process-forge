# Operator restart and CPU measurement

Explicit operator instruction: restart the existing pf-app-server (Runtime) and measure CPU. New exact Work; no terminal source-migration Work reused. Context ctx-20261016-091113-310bed is fresh, policy continue; capsule 36672fd9140733171ab72a9bfaecc10d9751cb1146b76387e3d9d4302fab86d5 is valid/ready and forbids product writes and subagents.

Owner is PID 13540 from the actual workplace runtime.lock, launched from the installed distribution. PID 9308 is its launcher; connected MCP PID 5284 is separate. Installed version is 1.2.0, but journal/service hashes differ from current SQLite source. Restart alone does not install the fix. No update, migration, hook/MCP restart or general 1.2.0 qualification is authorized by this Work.

Plan: measure 30 seconds before, inspect guarded shutdown/active work, use existing operator lifecycle, verify a new owner/readyz, measure startup and then at least 60 seconds in a settled process. Device CPU is process kernel+user delta divided by wall time and logical CPU count. Retain timestamps, process creation identity, exact result and service caveats. No OS-kill or guard bypass.
