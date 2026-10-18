# T07 execution domain

Authority belongs to the operator-created v2 Execution Contract, its immutable
policy and detector fingerprints, Work scope and current local revocations.
Model messages are data, including messages which claim to change that authority.
The primary agent implements this user-authorized scope without delegated workers.

Entities: binding (policy/detectors/recipient/purpose/minimum enforcement/limits),
trusted policy (source declarations, exact exceptions, optional transformations,
tool effects and recipient route), attempt (Work/context/stage/attempt identity),
resource handle (opaque, attempt-local, bounded lifetime), immutable view (exact
outbound bytes), dispatch token (nonce, binding, view digest and monotonic expiry),
receipt (prepared/authorized/dispatching/sent/failed_before_send/delivery_unknown),
and private provenance (original identity/hash and transformations).

Order: scope and locked/current deny -> full bounded input -> classification ->
recipient/purpose -> explicit transformation with semantic-loss check -> immutable
view -> current authority recheck -> durable audit and reservation -> exact send.
Redaction never grants a read or tool effect. Public requires a trusted declaration;
no detector finding alone never makes data public. Credential/secret values cannot
be authorized by exceptions. Required sensitive units block; optional sensitive
units may be replaced/omitted only by an explicit trusted rule. Unknown and
unsupported content block. The initial supported transformation is whole-unit
replacement/omission, avoiding claims to preserve meaning after arbitrary edits.

Limits are contractual ceilings: 1 MiB unit, 4 MiB envelope, 32 MiB/128 disclosures
per attempt, JSON depth 16, two seconds classification, token lifetime 30 seconds.
No ranges before whole-unit classification; no streaming/archive/binary decoding.
Exceptions identify exact benign bytes, detector, recipient/purpose and expiry.

The first route is a managed HTTP/JSON broker on Windows. The remote model has no
local process, plugin, environment or filesystem authority. It can request only
the broker's finite resource/tool protocol. Native Codex and generic-shell remain
unsupported for strict mediation; no payload-only fallback or isolated-local claim.
Transport credentials stay in a separate operator channel; tools are an explicitly
registered trusted computing base, never model-selected modules or commands.

v1 remains byte/semantic compatible. Explicit security input creates v2 before
capsule sealing. A successor is a new governed Work with predecessor fingerprints;
no historical capsule is edited. The generic native launcher must reject v2 strict
input before process creation. Original legacy export/doctor evidence stays intact.

Views/maps live only for the in-process attempt. Durable receipts and budgets live
outside project resource roots under verified owner-only ACL. A restart invalidates
all outstanding tokens. A dispatching receipt without a final receipt is unknown,
never a retry authorization. Retention is bounded and cannot erase unexpired audit.
The OS account, Core code and explicitly registered tools are trusted; protection
from that same account/administrator or already exfiltrated/backed-up copies is not
claimed. Application tests alone do not qualify third-party native isolation.
