# Metrics and operator domain

Registration count is historical catalogue size, online presence is a TTL-qualified ledger report, running worker count is a persisted worker-state report, and lease held count means active and unexpired lease records. None alone proves an agent is computing or the whole system is healthy. Run in_progress/blocked counts describe workflow records; user-wait remains unknown without a specific contract. Keep these labels explicit.

Every metric group includes source, complete/partial coverage, observed counts, issues and sample time. Invalid, future, oversized, unavailable or unvisited records cannot silently become zero. Observed partial counts may be shown as lower-bound observations; exact values are null unless coverage is complete. Metrics belong to a Runtime instance and expire independently of service-state freshness. Offline/changed owner invalidates current activity claims.

Metrics never include identities, paths, raw errors, chats, prompts, arbitrary log text or secrets. Enumeration/read/parse budgets and symlink/containment checks bound work; no recursive unrestricted scan. Runtime owns snapshot production; a viewer never recomputes the domain or changes state. Existing mandatory event journal remains independent from optional diagnostics/metrics.

Guarded shutdown is explicit operator action. Require advertised capability and expected instance, refuse observed running workers/unknown coverage/in-flight requests unless force is explicit. Prevent new Runtime requests once stopping is committed, but independent file-first clients are not globally frozen by the observer server. Q/Esc/Ctrl+C in monitor never stop Runtime.

Profile configuration edits a chosen project/Work/session layer, preserves other scopes, respects existing locks and T09 expiry/budget rules, and validates effective settings before writing. Planning/status have no writes. Optional detail remains separate from mandatory events and authorizations.
