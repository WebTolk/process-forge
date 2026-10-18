# Delivery domain rules

Source, clean candidate, archive, installed files, running Runtime and connected MCP are separate identities. Owned files are exactly core manifest paths; unknown files belong to the operator and must survive. Release inventory normalizes text endings; compare released content for source parity and raw archive bytes for manifest verification.

Update order is Core then compatible Workplace migration then separately assessed projects. No project migration is implied. Backups and update journal prove recovery boundaries; never blindly retry after partial apply. Use core-update repair classification before recovery. Do not force through locally modified files. Runtime stop/start affects only the verified named owner and only after checking worker/jobs ownership. Host-owned MCP process is not killed for reload; current host success is not new-code acceptance.
