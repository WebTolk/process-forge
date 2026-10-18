# Ordered journal error-row replay, 2026-10-16

Status: independently accepted source correction. A separate cumulative private
development archive, install and actual Runtime profile are required. Public
1.2.0 remains gated by a detailed report and explicit approval.

The existing Core ProcessEventJournal owns one bounded memory-only index of
first ID positions and ordered bad/blank rows. Every lookup reads and hashes
the whole current journal. Changed bytes, an unknown parser or reader, deeper
parsing callers, missing IDs and the 16 MiB metadata bound retain ordinary scan
behavior. A cold early duplicate does not publish partial facts. Bad rows before
the first target are parsed again; read-only Host lookup preserves blank-row
handling and falls back for older or fake Core collaborators. No new public
CLI/MCP/schema, disk cache or access authority is introduced.

Error policy changes resume scanning strictly after the consumed row, without
repeating its constructor or an earlier prefix. Optional policy-comparison
allocation failure is a miss. After bad history, only a recognized ordinary
stdlib C-backed serializer may extend new-record facts; unknown producers drop
metadata without an additional post-fsync error constructor. Preparation,
cross-process guard, bytes, flush/fsync, duplicate behavior and post-lock hooks
retain their existing boundary. The legacy CLI wrapper is unchanged.

The initial independent v2 review rejected R1/R2; its evidence remains intact.
R1/R2 were verified by the second review, which rejected R3. Exact native
string types now precede separator comparison, avoiding user callbacks; the
third narrow review accepts this correction. They passed the original concurrency smoke with
necessary observable regressions, unchanged raw-ingress controls and bounded
old/new failure, ordering, durability, memory and four-writer checks.

On the same 101,379,731-byte historical corpus with one malformed row, five
alternating pairs of four calls, including a cold first call, preserved results
and exact output bytes. Median append wall/CPU seconds were 5.197518/4.84375
to 2.511963/2.109375; read-only lookup 5.470902/5.296875 to 1.866624/1.671875.
The older installed Runtime was active; admission/preparation of the final
narrow native reviewer overlapped some source samples. These are source operation observations,
not quiet Runtime CPU, Work creation, installed or connected-host acceptance.
Every current read/hash remains linear; external writes invalidate the facts.
