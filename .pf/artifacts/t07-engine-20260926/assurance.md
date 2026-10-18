# T07 source assurance accepted

Final exact source hashes and bounded 30-file delta: assurance-results.json.
All 14 distinct required source commands pass after recorded fixes. Final T07
suites: engine34 + actual Work10 + TLS/transport8 = 52 checks. Other coverage:
existing complete v1 capsule parity, Work resources, both prepared execution
suites, Work start, Runtime metrics/server operator, multiprocess event journal,
actual repository schemas, checksum inventory and public cleanliness. Final
changed Python files parse with their existing UTF-8 BOM handling.

Independent primary-agent review after implementation (single-agent pinned
process; no delegated reviewer): checked trust inputs, exact schema framing,
scope-before-open, Windows handle/ACL ownership, policy/detector binding,
current-deny and Work-stage serialization, secret/credential paths, one-shot
nonces, durable reservation ordering, ambiguous send recovery, retention and
v1 migration. Serena's Python backend remains unavailable; targeted source,
AST and actual execution provide the evidence.

Findings closed before acceptance:

- Standard TLS defaults could use ambient key logging/trust files: replaced by
  explicit Windows-root context. Actual TLS capture and environment negatives pass.
- Exception could expire after preparation: immutable view carries its expiry;
  later authorization refuses it. Tool code/config drift is also checked.
- Work stage could change between authorization and send: actual Work commands
  and disclosure now share the Run OS guard. Live-stage and guard tests pass.
- Native v2 preparation rejects before prompt construction; actual previous
  installed v1 reader rejects v2. Context and predecessor hashes stay immutable.
- Concurrent-reservation fixture initially requested more outstanding tokens
  than the new contract permits. Corrected it to race for one remaining slot;
  one winner, no overspend. Initial failure is retained in source test evidence.
- Existing T10 HTTP test assumed client receipt implied server-finally completion.
  Added explicit handler/Event completion waits in that test only, under the
  separately recorded assurance scope amendment. Runtime code is unchanged.

The first aggregate checksum failure reflected the recorded in-progress test
correction; final inventory and every source check now pass. The original failed
aggregate is preserved, not rewritten into a green run.

Actual historical proof: historical-preservation.json. A conservative new
derivative of the original T06 Run contains whole-unit replacement only. Exact
exception covers known long generated YAML identifiers, while private-path/hash
findings still redact the entire unit. Original Run/capsule hashes and the exact
single doctor FAIL remain unchanged. No network send occurred for that export.

Matrix A01-A28 maps to named cases in final-smoke_egress_*.json, historical proof,
and I01 native-feasibility.json. Native wrapper bypasses are demonstrated, not
misreported as isolation. Codex itself was not sandbox-qualified. The managed
route's finite protocol, actual TLS/HTTP framing, refusal channels, source-swap,
crash and failure fixtures are distinct evidence. No host-owned MCP reload claim.

Synthetic benign corpus: 5 samples, one conservative email false positive before
an exact valid exception, none after; expiry/changed bytes reject. This tiny
corpus is not a production false-positive estimate. Final reports include measured
1 KiB/64 KiB/1 MiB classification latency and Python allocation peaks, all within
the declared classification ceiling on this machine. No SLA is inferred.

Browser verification: not_applicable. This scope adds no browser UI; actual
authenticated/managed HTTP recipients and native CLI/operator tests are used.
Native provider isolation, other OSes, arbitrary vendor APIs and host MCP control
remain explicit unsupported boundaries, not silently downgraded features.

Next: release-delivery using a clean detached candidate, official release-pack
and archive qualification, installed core-update plan/apply with automatic backup,
full payload preservation and installed broker qualification/capture.
