# MCP session read-model design

`pf.session_context` is bounded to current project/work facts, blockers, presence, freshness and 20 normalized session events. `pf.session_chat` pages the trusted redacted transcript (1--100 items, role filter, cursor/before). `pf.session_activity` returns at most 100 normalized event facts.

The models omit raw journal payloads, filesystem/private workplace references, and exception strings. The Core transcript export remains the sole content reader; `tools/pf_runtime/session_read.py` is the shared application read layer, so MCP contains no business projection logic.
