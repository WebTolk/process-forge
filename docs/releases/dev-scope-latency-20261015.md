# Development checkpoint: scope admission performance

Development version: 1.1.0. Executable source commit: `4b0b3433a8f08ffed6e291da2004d049ad87ef9c`.
Clean source tree: `55cc4d65cb9dab695103a581d6c94449b1fce8a6`.
Archive SHA-256: `8e560914d55acf0ab4aff236f95557c111fe48d0216651d163ae6b3d738fd181`.

The scope-overlap algorithm now belongs to the concrete Core-owned
`ScopeConflictService`, shared by admission, supervisor and plan validation.
Disjoint mandatory literal prefixes avoid unnecessary traversal; unresolved
glob pairs reuse one lazy normalized inventory per operation. Decisions,
reasons, order, forbidden precedence, dependency/handoff rules and live reads
are preserved. No cross-operation cache or new public contract was introduced.
See the [controlled before/after measurements](../audits/work-start-scope-latency-20261015.md).

The source still contains legacy composition and callbacks. CLI adapts requests
to `ProcessExecutionService`; the previous public version already used that
class. All five OOP epics remain open.

Two native PF peers independently checked archive bytes and the completed source
change. All 1,249 release members and 1,248 Core payloads matched their seals;
the eight changed committed payloads matched the supplied Git blob hashes.
Source/extracted scope and recovery checks, archive quick checks and neutral
schema/public/checksum gates passed. This is focused qualification, not a new
complete public-suite pass. Symlink qualification was unavailable on the host.
Review environment failures and evidence boundaries remain in private records.

The native updater applied this exact archive once without force. It verified
1,247 installed owned payloads, preserving one unchanged pre-existing local
manifest exception. All 22 backup preimages, three static configurations and
695 protected history/capsule files matched. No incomplete update remains.
Installed scope, recovery, HTTP body, Unicode transport, context and doctors
passed. The Unicode fixture uses controlled bootstrap; a separate ordinary
installed stdio process also initialized and read the real context and Work.

| Installed operation | Observed seconds |
| --- | ---: |
| Scope validation, five-sample median | 1.388492 |
| Persistent ordinary MCP Work state, five-sample median | 3.703608 |
| CLI context check, five-sample median | 1.819772 |
| Complete CLI Work state, one sample | 6.539269 |
| Complete useful scoped Work creation, one sample | 19.856115 |

Read timings used a stopped owned Runtime and warm filesystem. The creation
sample used the actual active Runtime/backlog; it includes process startup,
guards, publication and final state. It is not a distribution or a comparable
before/after ratio. Exact-selector state still scans the historical catalog:
in a separate instrumented sample, catalog 8.285s of state 8.432s and 1,353 document
loads. Instrumented time is not substituted for the unprofiled timings above.

GitHub v1.1.0 (`06acea7bcfe1bb5d7d009feb250e72c52b95e671`) and this dev code
were compared on identical generated data: 855 history pairs and 2,000 files,
five samples per version. Common Work creation medians were 13.645990/6.963371s;
identical scope-validation medians were 4.632357/0.653523s. The old common API has no scope-file;
the dev common request has empty grants and blocked execution readiness.
Those creation results do not compare equivalent useful executable Work.

The two previously failing isolated native checks now pass unchanged budgets:
task batch 57.00s/180s, long-lived Runtime 67.84s/240s, sequential without a profiler.
The real shared Runtime has a fresh installed process identity but remains
degraded. A 45.011s OS sample observed 44.8125s of process CPU, almost one core.
A separate 20s nonblocking py-spy sample mostly captured supervisor collection,
prepared-input semantic validation and context/resource loading. It retained
487 successful samples and 231 stack-read errors; no exact CPU percentage or
idle baseline is inferred from that sampling profile. The scheduler failure
cause and a safe retry-cost repair still require bounded investigation.

The application's actual connected MCP host remains unqualified for these new
modules. A fresh Runtime or independent stdio process does not qualify that host.
Residual catalog latency, shared Runtime health, legacy MCP diagnostic routing,
and complete accumulated source/archive/install/connected-host qualification
remain open. This checkpoint is **not ready for stable 1.2.0 publication**.
Public 1.2.0 tags/assets/stable-channel changes require separate operator approval
after a detailed readiness report; none were published by this checkpoint.

This portable note and its checksum are a separate post-install documentation
commit. They are not part of the executable archive identified above. Private
governed records retain exact receipts, source/remote readbacks and review limits.
