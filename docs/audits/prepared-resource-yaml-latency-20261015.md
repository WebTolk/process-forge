# Bounded prepared resource YAML parsing — 2026-10-15

The bounded prepared snapshot reader now uses the existing Core safe YAML
parser. Its default backend is CSafeLoader when available, with the existing
Python SafeLoader fallback. No dependency or new cache was added.

The path/symlink/containment, size, current byte read, UTF-8, mapping-type and
raw-byte hash checks retain their order and machine-readable failures. Native
collection still performs all prepared-input, source, resource, current-access,
stage, output-attribution, lock and recovery checks.

## Comparable measurements

Five alternating native collect-engine samples per implementation used one
unchanged governed fixture from the existing recovery smoke. The first native
collection had already sealed its receipt; repeated collections still performed
the real validation. The baseline reader was extracted verbatim from Git commit
`9b81359252c340fd45fb519ed361a32412b84a38`; the other reader was the actual changed
source. Source startup/import/setup were outside timing. The shared installed
Runtime remained active, so these are warm measurements under background load.

| Operation | Before median | After median |
| --- | ---: | ---: |
| Native collect engine | 0.719005 s | 0.643369 s |

Every result hash and the complete fixture byte inventory matched the original
baseline. A separate counted invocation retained 395 total YAML parses:
387 C / 8 Python before, 389 C / 6 Python after. Counts and cProfile were excluded
from the five timing samples. This is a modest improvement of about 11% in this
fixture, without a measured live Runtime CPU or complete Work-creation claim.
One pair was 7.84% slower; the five pairs do not establish a stable performance
guarantee or statistical significance.

An earlier isolated experiment added the existing operation parsing cache:
395 parses became 64, but the median increased from 0.687107 to 0.859389 seconds.
It was rejected and never applied to product source. Fewer parses alone did not
establish faster execution.

## Qualification and remaining work

The bounded-reader characterization matched 38 ordered cases, including 15
current/historical snapshot files with 14 distinct raw hashes, typed opaque values, aliases/cycles, BOM, malformed
and unsafe YAML, invalid UTF-8, non-mapping roots, path/size refusals, fallback,
mutation isolation and same-size/same-mtime changes and deletion. Its normal
Core-only import did not load the legacy CLI. The symlink control in this matrix
is inert. No physical symlink/junction test was run for this helper; the existing
recovery smoke's physical junction controls exercise a different private-path
boundary.

Existing source checks passed unchanged native budgets: prepared context
59.58s/360s, prepared recovery 32.41s/240s, request scope 0.59s/180s. No new smoke
entry or timeout increase was introduced. Independent review and exact delivery
receipts are retained separately in governed records. The independent reviewer
accepted the source change with conditions and no blocking finding. It reproduced
all 38 rows, rehashed the 162-file native fixture and recomputed the distributions;
it did not replay native collect or rerun the three complete smokes.

The review also confirmed a backend syntax difference with PyYAML 6.0.3:
an interior plain-scalar tab emitted by the native emitter, or a tab after a
mapping colon, is accepted by the C backend and refused by Python. A handwritten
unpaired-surrogate escape has the reverse boundary outcome. No loss of an
already successful native preparation was demonstrated. The retained corpus
parity is bounded; universal SafeLoader equivalence is not established.

The fix delegates parsing to an existing Core owner. Legacy callbacks in prepared
resource authorization remain unported; all five OOP epics remain open. Catalog
selection and repeated context construction remain separate costs. Source,
archive, installed Core, live Runtime and the application's connected MCP are
separate qualification layers. This source result does not establish stable
1.2.0 readiness or authorize publication.
