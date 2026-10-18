# F06-F08 implementation and primary acceptance

Status: primary acceptance PASS; independent review pending.

The junior PF shell worker implemented initial fixes but was stopped through worker-run-stop after repeated Windows sandbox limitations and an unconfirmed final command. No successful worker exit is claimed. Primary explicitly took ownership; original worker files are preserved in worker-original/.

Primary corrected the worker stale-reaper close/unlink race and potential descriptor double close by using a persistent OS-locked .lock.guard file. All modern acquisitions, metadata recovery and release hold that same guard; it is never unlinked. The legacy .lock metadata remains compatible, with live/unknown/foreign owners preserved and dead aged owners recoverable. Release checks owner identity/token. Fixed Win32 ctypes handle signatures and conservative liveness failures. Concurrent old executables that do not implement the guard remain outside this cooperative protocol.

F07 uses the existing JSON reader, recognizes flat and nested presence records, skips corrupt/non-object/offline records, and preserves the active organized-session guard on Director disabling. F08 uses one report-default helper shared by task report lookup and plan normalization. Missing required plan fields still produce validation errors; diagnostic normalization no longer raises NameError.

Source files: tools/processforge.py, tools/smoke_cli_audit_f0608.py. Checksum owned by primary.

Evidence in parent artifact directory:
- baseline-reproduction.json: all three original failures reproduced on committed 5c95391.
- f0608-primary-final.txt and f0608-primary-final-2.txt: expanded smoke PASS, including live legacy owner, dead owner recovery, exception/foreign/malformed lock handling, four-process 32-update exclusion, actual CLI Director refusal/success and actual CLI normalized output with report omitted.
- f0608-portable.json: public-copy PASS; original CLI negative control exits 1 as expected.
- related-registry.txt, related-authoring.txt, related-coordination.txt: existing smokes PASS.
- f0608-schema.txt: schema PASS. f0608-cleanliness-2.txt supersedes scanner false-positive from platform.node; socket.gethostname preserves host semantics.

Boundaries: Windows host exercised; POSIX flock branch requires CI on POSIX. Persistent guard files are intentional local synchronization state. Neither arbitrary filesystem mutation by non-cooperating processes nor hostile metadata writers are claimed safe. Full source release qualification remains separate due intermittent Runtime startup failure; standalone long-lived and five diagnostic ingress attempts passed, full run failed.
