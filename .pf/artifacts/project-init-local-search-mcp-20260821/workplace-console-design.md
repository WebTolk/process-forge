# workplace-console-design

Source: accepted `project-initialization-contract.md`.

This is design only; no web console is part of the implementation slice.

The future console has five read/proposal surfaces: initialization status and doctor facts; snapshot-authorized resource search; configured/activated/visible/verified MCP matrix; Codex integration verification; and an ordered repair plan. Its default action is dry-run/proposal. Any mutation requires an explicit apply confirmation and uses the same Core initialization service as CLI/MCP.

It must never display private absolute paths or secrets in public/export views, create specializations implicitly, bypass snapshot authorization, or turn MCP into a raw ingress API.
