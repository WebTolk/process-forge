# domain-modeling

The Runtime owner is identified by instance_id + runtime.lock + PID/creation time and authenticated readiness, not process count. Parent launcher and actual MCP are separate processes. Device CPU equals delta process user+kernel CPU time / elapsed monotonic wall time / 4 logical CPUs. Startup is separated from settled observation. Guarded idle status is an execution condition; unknown worker activity must not be silently changed to zero. Restart reloads installed code and does not install the SQLite source.
