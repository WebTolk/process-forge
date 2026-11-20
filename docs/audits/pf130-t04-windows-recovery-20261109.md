# T04 Windows recovery and negative-path qualification, 2026-11-09

Status: passed for the bounded Windows source-service/CLI profile below.
Tested source: `a3714b2c4065317be7ec28731b20d1f0ad721161`.
This delivery adds documentation and its checksum entry; PF executable code,
maintained test bodies, configuration and safety guards are unchanged.

Python 3.11.9 and pytest 9.1.1 completed 186 tests, with no failures, errors or
skips. The registered Python QA launcher selected the real project interpreter.

| Profile | Passed | Exercised behavior |
| --- | ---: | --- |
| Publication and recovery | 49 | Short writes, fsync/link faults, pre-intent retry, immutable Work identity, start rollback and terminal completion replay |
| Storage negative paths | 57 | Physical identity, admission isolation, pending/foreign storage and frozen errors |
| Admission and diagnostics | 68 | Owner isolation, safe diagnostics, malformed and oversized stopping-state refusal |
| Journal recovery | 11 | Interrupted batches, barriers, source drift, corruption and missing/replaced storage |
| Journal concurrency | 1 | Existing six-producer SQLite smoke, deduplication, transaction rollback, indexed lookup and outbox flush |

The terminal completion matrix exercised failures before and after nine
publication points, including the intent, authoritative assignment, event and
cleanup. Invalid intents were refused without writes. Fault injection and
synthetic interruptions do not establish real OS-crash or cross-boot durability.

A fixture adapter replaced the original stdio-MCP bootstrap with the same
file-only CLI initialization and a direct Core service start. The maintained
assertions and fault injections were unchanged. This profile does not qualify
stdio MCP, an installed Core, a connected host, a device or a release archive.
Owned fixture evidence was retained; an observer refused model and Runtime/MCP
service launch attempts. No such launch was attempted by the observed test
process.

## Observed completion refusal and recovery

A normal source CLI completion replay failed closed in
`ExecutionAdmission.check_stopping`: its bounded read returned 65,537 bytes,
exceeding the existing 65,536-byte stopping-state budget before JSON parsing.
The error propagated as `execution_activity_unknown` through storage admission
and mandatory process-event publication. The durable completion intent remained
available for supported replay. The full document contents, validity, producer
and process liveness were not established.

A later read-only guard check passed with a bounded ready document; supported
public replay then recovered the pending completion intent. No guard, live state
or infrastructure was changed to obtain that result. Recovery of availability
does not establish a producer fix or explain every historical occurrence of the
same error code. Investigation of the document producer and its size budget
remains separate.

## Acceptance limits

The source checkout's 10,044 tracked baseline files were unchanged during the
tests. Earlier immutable-publication evidence was referenced only after matching
the relevant test/helper hashes; those earlier tests are not added to the
186 fresh passes. The deferred universal first-import case was not rerun.

No executable PF Python changed in this delivery. Real Linux qualification
remains a separate release gate. The new documentation digest is verified;
the full inventory still has its pre-existing stale `.pf/AGENTS.md` entry.
Neither that inventory gate nor stable release readiness is declared passed.
