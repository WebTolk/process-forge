# Journal domain rules

Project event journal is source evidence; an invalid fragment is uncertainty, not a valid event. Raw ingress and project derived events are distinct stores; no full event may be invented from a timestamp. Quarantine preserves original bytes and explains the gap. Blank lines are already a supported reader behavior, not a schema waiver.

Each appended event id must be deduplicated under the same writer lock as the append. Serialize a whole UTF-8 JSON record before acquiring/writing; preserve a trailing newline and flush durable bytes before reporting success. Dispatch hooks after releasing the journal lock to avoid reentrant deadlock. A lock failure is an explicit operation error; do not silently drop events or falsely acknowledge delivery. Existing raw receipt/replay remains the independent recovery layer.

Loaded old processes retain their code until real restart/reconnect. Source concurrency tests prove the fix for new-version writers, not retroactive reload of all host processes. Source installed through official Core updater later; no live hot patch. Current byte-range repair can preserve appenders without requiring them to know a new lock protocol.
