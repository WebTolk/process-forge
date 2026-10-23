# Domain rules

Context freshness and required-resource readiness determine whether Work may run;
search availability is a separate derived observation. Missing/stale/building or
failed search never causes automatic maintenance or a refresh/retry side effect.
Required context resources and all current access/material checks stay strict.

The workplace owns the physical resource index. Manual maintenance requires an
explicit workplace target and apply; an agent needs separately authorized workplace
scope. Project initialization, refresh, repair, context reads and search do not
grant device maintenance. Existing query-time snapshot/Work filters remain in place.

Only one workplace maintenance writer runs at a time across manual/Runtime clients.
The serialization mechanism releases on process death; durable running/failure
state never claims fresh ready. A subsequent authorized pass recovers/retries
without deleting history, changing grants or requiring an infrastructure restart.
Partial indexing failures remain visible; no swallowed required writes.

New code owns narrow responsibilities and has no reverse call to Main/Runtime.
Construction is cold. Operations read current documents; no lifetime cache of grants.
No new general scheduler, DI framework, external dependency or all-Core migration.
