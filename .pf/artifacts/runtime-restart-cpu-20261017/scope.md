# Scope and acceptance

Operator request is the existing pf-app-server restart and device CPU measurement. Managed lifecycle only; ready owner must be verified, shutdown activity guard respected, old PID exit and new owner identity/readiness observed. Observe initial startup separately from a settled 60-second window; normalize CPU to total logical processors. Include the old launcher and connected MCP in the baseline to avoid attributing their CPU to the owner.

Only private artifacts/logs/scratch are written directly. The user explicitly authorizes the existing Runtime lifecycle action. No update/install, migration, MCP/host-hook changes, other worker termination or unrelated project repair. Installed source still differs from the SQLite commit, so the result qualifies restart behavior of the installed 1.2.0 only.
