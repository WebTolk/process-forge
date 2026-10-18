# Journal recovery lessons

The unlocked append defect was demonstrated independently of historical corruption: a real four-writer run accepted three duplicate ids before the change, and the unchanged test passed with the shared writer boundary. Keep root-cause confidence precise: that race is proven; the old timestamp fragment's producer is not.

For operator recovery of active append-only data, a verified fixed-length historical range update can preserve offsets and concurrent suffix additions. Require a durable full-prefix backup, exact fragment identity and after-write byte proof; reject unexpected/multiple/unterminated corruption and prefix drift. Keep raw evidence outside schema-scanned NDJSON and retain an explicit audit record.

Reuse the established registry OS-guard/owner protocol and dispatch external effects after releasing locks. Do not create another ad hoc lock/recovery algorithm or silence malformed data in validation. No global rules/process versions/memories were changed; this is a scoped project-level proposal supported by test evidence.

Next: complete local T10 bounded metrics/operator improvements, then deliver both qualified source deltas through the standard Core updater. The installed monitor update remains successful; this source fix is not retroactively claimed installed. Native POSIX execution and genuine connected-host reload proof remain distinct from Windows source/package tests.
