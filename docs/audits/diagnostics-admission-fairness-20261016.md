# Windows diagnostic lock admission, 2026-10-16

Status: independently accepted source correction, commit
`17206a1b335ea5d1c10ce374896cd2b3c729ffed`. Cumulative archive, installed
execution and Runtime profiling are recorded separately in the
[development delivery](../releases/dev-journal-lock-20261016.md).

The original diagnostics smoke failed its Windows multiprocess storage check
even while the shared Runtime was stopped. Repeated investigation found
50 ms lock-admission failures. Reducing polling to 1 ms still failed and was
rejected. No timeout or assertion was relaxed.

Windows admission now passes through a process-shared named mutex before the
same existing byte lock. One deadline includes the thread lock, admission,
byte-lock retries and sleeps; late grants are refused and acquired resources
unwind on every failure. The byte lock remains the exclusion authority for
mixed old/new writers and path aliases. Mutex identity uses normalized lexical
absolute paths, avoiding repeated directory-handle resolution on the hot path.
Unrecognized junction/subst aliases still depend on the byte lock. This does
not establish FIFO fairness, cross-session fairness or universally loss-free
logging under arbitrary I/O stalls.

The existing JSONL sink/logger, privacy, rotation, retention and quota bodies
remain unchanged. Thirty source controls cover API failures, negative paths,
threads, recognized aliases, abandoned mutex ownership, new/new and mixed
writers; body overlap was not observed. Five new/new pairs had zero failures;
a mixed-version pair retained one admissible timeout loss. This is reported,
not hidden by retrying or extending budgets.

The final original full smoke passed unwrapped: JSONL 10,000 operations took
14.50288 s within its original 20 s limit, memory sink 0.4314/5 s and disabled
logging 100,000 operations 0.09427/0.5 s. An earlier unwrapped candidate exceeded
the JSONL limit at 20.8893423 s; that failure is retained. The change between
those candidates removes expensive canonical-path resolution from mutex-name
construction. Instrumented 1,000-name profiles changed from 0.319318 s to
0.0095543 s; these profiles are separate from ordinary smoke timings.

These are source and targeted correctness results. Installed and shared Runtime
behavior require the cumulative delivery checks; actual connected-host proof
and full public-release qualification remain separate. Stable 1.2.0 requires
the detailed readiness report and separate user approval.
