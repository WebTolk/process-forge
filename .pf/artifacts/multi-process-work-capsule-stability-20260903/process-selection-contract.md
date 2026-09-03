# Process selection contract

Status: ready_for_review

The public MCP, Core and CLI all accept optional `process_id`; existing calls containing only an objective remain valid. The selector is deterministic and does not classify natural-language objectives.

| Input | Result |
| --- | --- |
| Legacy singular process | Select that one process. |
| One allowed process | Select it. |
| Explicit allowed id | Select it. |
| Explicit undeclared id | `process_not_allowed` or `process_not_found`. |
| Multiple choices without an unambiguous default | `process_choice_required` plus compact candidates. |

All diagnostics are machine readable. The implementation never searches a process outside the manifest/snapshot/catalog boundary.
