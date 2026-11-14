# MCP connections and Core updates

The stdio entry is `tools/pf_runtime/mcp_server.py`. Its transport process keeps
the host's pipes open and invokes the fixed native entry in a fresh child for
each backend request. A compatible replacement of the Core can therefore serve
the next request without replacing the host's connection. The transport retains
discovery subscriptions; it retains no Work state, permissions or executing
business Core.

Each child repeats the native publication/admission checks, request validation
and existing project/session/Work binding. A new process does not establish
storage safety by itself. Native adoption, publication identity, epoch and actual
writer exclusion retain their existing owners. An incomplete or incompatible
publication can refuse a request even while the transport remains available.

The transport answers MCP ping locally; transport liveness does not prove Core
or storage readiness. Invalid protocol is rejected before business Core dispatch.

The advertised MCP protocol remains `2024-11-05`. The connection exposes the
existing typed tools and the metadata resource `pf://core/identity`. That resource
reports the executing Core's loaded identity, including an explicit unknown or
partial status when distribution metadata is unavailable. Metadata labels do not
prove payload integrity. Other resource URIs do not permit filesystem reads.

The transport compares tool and resource catalogue fingerprints after a backend
response. It sends `notifications/tools/list_changed` or
`notifications/resources/list_changed` for a catalogue already listed by the
client, and `notifications/resources/updated` for subscribed resources whose
revision changed. Changes are observed on the next request; there is no idle
poller. Clients must refresh their callable schemas before using changed tools.
Actual host refresh behavior needs qualification independently of wire clients.

Backend failure can leave the outcome of a mutation unknown. The transport
returns a tool error with `outcome: unknown` and `automatic_retry: false`; it never
replays the request. The caller must inspect the exact durable Work or operation
receipt before deciding how to recover. Backend stderr is not returned to the
model. The next explicit request can use a recovered backend on the same pipes.

Backend execution has a 120-second watchdog, configurable by the host through
--backend-timeout-seconds. A timeout also means an unknown outcome; it does not
authorize replay or termination of separately owned workers. Response framing
uses LF only and preserves Unicode line separators inside JSON string data.

The internal `--backend-request` entry and `processforge/backend` result metadata
form transport contract version 1. This is a fixed-distribution interface, not a
model-selectable executable or permission grant. Compatible Core releases must
preserve the negotiated protocol and previously published callable contracts.
Changes requiring a new transport contract need an explicit host connection
upgrade; the bridge does not translate arbitrary MCP protocol generations or
reload Python modules in place.

PF Core installation maintenance and package updates have separate lifecycles.
An ordinary package update does not request workplace maintenance or require
every project agent to pause. Package locks, verification, metadata and rollback
remain with the package owner. A package operation still respects an already
applicable native fence on shared resources. Neither catalogue refresh nor a
package update changes an active Work's immutable capsule or pinned permissions.

The source integration tests exercise the real stdio entry on isolated consumer
distributions, including changes to executing Core logic, UTF-8 catalogue data,
subscriptions, backend failure and session mismatch. They do not replace native
sealed-publication, installed-Core or actual-host acceptance.
