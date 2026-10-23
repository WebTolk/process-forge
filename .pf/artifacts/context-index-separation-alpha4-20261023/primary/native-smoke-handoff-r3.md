# Native smoke adaptation after lossless invalidation

The r8 scoped profile passed checksum, init/MCP, composition, narrowing, context
lock and workplace-index checks. Operational hardening failed its old assertion
that a resource event directly writes SQLite index_state last_error. This is the
exact second writer/lost-notification path rejected by independent review r1.

Update only tools/smoke_search_update_operational_hardening.py: retain its actual
source diff, schema corruption/rebuild, deletion and concurrent query assertions.
For the resource-event boundary, assert canonical read-only observation reports
the durable pending token, then explicitly call the shared maintenance owner and
prove recovery/acknowledgement. The existing minimal fixture has no registered
workplace catalogue; inject its already-authorized snapshot only at that catalogue
admission seam, while SQLite, event journal, token, writer and state remain real.
The separate workplace-index smoke covers actual registered catalogue composition.
Never restore direct SQLite mutation in the resource event or weaken data checks.

Primary owns this sequential QA correction under a separate one-file scope. No
fifth native contributor, infrastructure action or scope expansion is introduced.
After completion, rerun the affected native check and broader related search
smokes before freezing a fresh independent review candidate. Prior failed receipts
and the original r4 candidate remain immutable and available.
