# T07 implementation architecture and decisions

Implement a small provider-neutral Core package `processforge_core.egress`:

1. `contracts` validates strict operator policy/binding, canonical hashes, fixed
   detector version, finite limits and native admission. v2 is opt-in only.
2. `policy` fully decodes bounded UTF-8/text or JSON, checks nesting, classifies
   all bytes and applies whole-unit optional replacement/omission. Rules never
   come from model messages. Exact benign exceptions cannot bypass strong secret,
   credential, locked or scope denials. No broad custom regular expressions.
3. `storage` creates/verifies Windows owner-only private storage, cross-process
   lock, atomic fsynced state and mandatory receipts. Session views and reverse
   maps are memory-only; receipts/budget survive crashes. No nonce restoration.
4. `engine` owns prepare/read/tool/authorize/dispatch/export/close. Scope checks
   precede reads; exact source digest and non-reparse containment are checked on
   open and rechecked at dispatch. Immutable view bytes never come from rereads.
   Current policy/Work authority and revocations are serialized with reservations
   and dispatch. A stored dispatching outcome is conservatively delivery_unknown.
5. `transport` implements one fixed HTTP/JSON protocol, no redirects, proxies,
   SDKs, streaming, model URLs, plugin imports or subprocesses. HTTPS uses normal
   certificate validation; numeric loopback HTTP is an explicit fixture route.
   Fixed headers and credential-only transport channel are separate from content.
   Only complete, bounded, exact-schema model operations enter the broker.
6. `service` connects actual pinned Work validation and the operator CLI to that
   engine. Work creation accepts an explicit validated egress intent before capsule
   sealing; a successor binds predecessor checksum and refuses objective-resume
   mismatches. Prepared native routes reject strict Work before raw preparation.

Allowed model operations: read a granted opaque resource, invoke an allowlisted
trusted local tool with an exact argument schema, or finish with bounded text.
The shipped tool set is pure and finite. An operator-registered privileged tool is
trusted code, has separately declared effects and credential channel, and cannot
be registered by model input. Its output fields/errors/attachments are filtered
as whole units. This trust boundary is explicit, not an OS sandbox for arbitrary
tools. The CLI exposes no arbitrary tool registration or shell execution.

Qualification is tied to code/config/OS identity and exact transport framing;
changes invalidate an outstanding session. Native adapters never receive strict
capability. Isolated-local execution remains unsupported. The connected proof
is an independently capturing loopback recipient using the installed broker;
it does not claim control over this Codex host's MCP or external model account.

Private store must be outside the project, named `.pf-egress-private`; general
Work/prepared resource walkers explicitly reject this reserved component even
when a broad ancestor is registered. Add `work_resource_material.py` to the exact
impact scope for that exclusion. No other scope expansion is authorized here.
ACL is established before any sensitive content and reverified before operations.
Private audit retention defaults to 30 days; attempt close/expiry removes memory
handles immediately, while receipts remain. No secure-erase/backup deletion claim.

Implementation order: v2 contracts and compatibility -> policy/storage -> engine
and exact transport -> Work/CLI integration -> adversarial A01-A28 corpus and
measured limits -> independent review/fixes -> clean candidate/archive/installed
qualification -> standard core-update plan/apply -> release/evolve closeout.
No stage is passed on the strength of this plan. Tests use synthetic values and
fake recipients. Original T06 diagnostics and prior T10 acceptance stay frozen.
