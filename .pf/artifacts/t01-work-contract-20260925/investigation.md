# T01 — source-backed investigation and impact

Baseline: a180ad624442d4fbe8ac1710073ef7d4c44babc4. No product patch in T01.

| Source | Current behavior | Contract consequence |
|---|---|---|
| src/processforge_core/process_execution.py:657, :680 | Pins effective process, raw snapshot checksum and selected knowledge IDs | Identity exists; stage resources and resource content/version bindings are not yet a complete read contract |
| process_execution.py:1315 | Governed _write_capsule writes minimal context with empty required_sources and process pin | Must converge with the richer assignment-capsule path in T03; do not describe current minimal capsule as complete |
| tools/processforge.py:12804, :12947 | Normalizes scope/outputs/access and writes checksum/capability-rich worker capsule; checks sources and overlap | Extract one neutral normalizer, retain legacy reader compatibility, isolate model/driver preferences from mandatory identity |
| src/processforge_core/garage.py:134, :159 | Search/resolve authorize from current project snapshot | Add explicit Work scope in T02; never silently redefine project-level API |
| tools/pf_runtime/mcp_server.py:65–201 | Shared services behind transport; session identity/project mismatch checks | Transport stays optional, consistent denial semantics must survive new Work selectors |
| tools/pf_runtime/host.py:798–866 | Codex hook/worker provenance conditions inside common Host; generic worker authorization follows | T04 moves interpretation to trusted adapters, keeps raw-first and common binding/path/hash checks |
| tools/processforge.py:19959 | Worker prompt requires MCP bootstrap for knowledge grants | T05 prepares authorized input before launch; no nested work.start or mandatory MCP for already-bound worker |
| tools/processforge.py:11038, :11048 | Recursive telemetry redaction plus append NDJSON | Do not replace obligatory process evidence with optional diagnostic logger; arbitrary context/bounds/failure behavior need T09 |
| schemas/context-capsule.schema.json, assignment/run/runtime-driver schemas | v1 supports additive properties and retains two capsule shapes; manual/shell drivers exist | Version explicit execution-contract block; legacy readers remain readable but missing grants cannot become broad access |

docs/concepts/context-capsule.md explicitly limits 1.1.0 selected IDs to an auditable
pin and calls narrower authorization future work. declarative-process-execution.md
already distinguishes deterministic file evidence from semantic review. Preserve both.

T08 live evidence adds two distinctions: global search index readiness versus
selected-project coverage, and declared resource availability versus resolvable
navigation. Its original snapshot/capsule are historical immutable inputs.

Local docs consulted first: installed local Psr/Log/LoggerInterface.php in the
documentation mirror confirms the eight methods, log(), placeholders and exception
context. Verified primary references on 2026-09-25:
[PHP-FIG PSR-3](https://www.php-fig.org/psr/psr-3/) and
[Python logging](https://docs.python.org/3/library/logging.html).
PF adopts an analogous Python interface; it does not claim formal PHP compliance.

Impact: T01 adds one public design document and one private ADR/matrix; no code,
schema migration, installed update or adapter registration. Later T09 touches
diagnostics boundaries, T02 scoped reading, T03 normalizer/capsule, T04 adapters,
T05 launch preparation; T06 verifies their composition. Each needs its own scope,
regressions and delivery, so the design cannot be mistaken for implementation.

Open design tensions resolved in domain/architecture: immutable contracts versus
mutable stage state; revoked authorization versus reproducible source; root metadata
versus content identity; mutable outputs versus immutable inputs; diagnostic off
versus mandatory process journal; trusted adapter registry versus untrusted ingress.
