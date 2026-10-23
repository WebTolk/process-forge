# Alpha4 source assurance before independent review

Whole existing/new pytest regression in the clean candidate:
`625 passed, 7 skipped, 6 warnings, 200 subtests passed in 252.84s (0:04:12)`.
Seven platform/environment-dependent skips and six SQLite ResourceWarnings were
retained in the raw receipt. Warnings surfaced during the existing hook-ingress
test; their origin is not proven by their reporting location. No warning filter
was added. Native archive/installed/actual connected-host acceptance is separate.

After that full run, four additional behavioral cases cover text CLI success and
failure, missing explicit workplace target, private factory failure diagnostics,
and a read-only observer failure. Production bytes did not change. Final complete
feature-suite run with branch coverage: `99 passed, 59 subtests passed in 49.93s`.
Ruff lint passed the two subsequently edited test files. All 21 owned Python files
passed lint and format before these test additions; the additions were formatted
by the registered launcher. No full-suite result with the extra cases is invented.

Five native source checks passed: checksum inventory; project init/local search
MCP; resource/snapshot composition; project resource narrowing; context lock model.
The exact command/exit/time/log hashes are in qa-receipts-r1.json. The final
candidate has 32 owned public files in source-candidate-r4.json; the unrelated
dirty Main/OOP54-55 bytes are preserved outside its sanitized Main projection.

Meaningful fixtures cover absent/stale/running/failed index, read-only metadata
observation and SQLite URI/timeout behavior, no automatic indexing/queuing/wait,
retained required-resource checks, current project/Work authorization and metadata
policy, explicit common CLI/job ownership, strict project snapshot boundaries,
bounded native writer locking, failure persistence, process death and retry.
Native contributor 4 measured 1538 documents/67 registered resources: first and
repeat refresh opened zero document bodies; explicit indexing opened the corpus.
Its instrumentation is source-open attempts, not physical I/O or a speedup claim.

SQLite FTS5 remains the actual workplace backend. Only the future scheduler job
callable is supplied; periodic scheduling, additional DB/vector backends and RAG
execution remain future work under the operator's clarified R2/R3/R4 boundary.
