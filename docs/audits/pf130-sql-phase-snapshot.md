# SQL phase snapshots before 1.3.0

SQL execution authority already selects an exact attempt through the indexed execution head. Preparing or collecting that attempt also takes a filesystem snapshot before publication. Previously this snapshot enumerated every attempt directory and retained the contents of historical preparation, retry, process and scratch files. Publication then reread those files under the existing admission and task locks.

The SQL path now selects zero or one directory from the authoritative head. It retains the complete existing file set for that head, including a terminal head used by collection. Root observations, assignment, capsule, configuration, prompt, prepared reference and explicit command output references remain checked. An explicit current reference can still point into the preceding attempt while projections are being replaced.

The selected private path is checked before interpreting absence. Invalid SQL routing, unsafe paths and unreadable state are refusals. An absent head does not permit choosing an attempt from status.json. Legacy retry publication retains its existing full snapshot.

This change narrows which filesystem changes can veto a SQL publication: an unrelated archived sidecar no longer does so. Current-file comparisons, allocation, SQL finalization CAS, start reservation, collection, callbacks and lock ordering keep their existing owners. No SQL transaction spans capture, process creation or waiting. A failed preparation can retain its planned allocation and recoverable preparation files.

## Verification

The maintained lifecycle suite covers public preparation, automatic preparation during start, synchronous completion and collection, repeated preparation, and preparation skipped for a real running child. Additional cases cover current-file conflicts, unrelated archived changes, missing heads, existing or unsafe directories, broken bindings and preservation of legacy file conflicts.

Run the suite through the configured Windows and Linux repository jobs:

    python -m pytest -q tests/executions/test_lifecycle.py

Scaling qualification holds current state fixed while growing terminal SQL history to 10,000, 100,000 and 400,000 records. It records selected files, actual SQL work, query plans, warm percentiles and fresh-process observations separately from fixture population. A fixed file set does not bound the size of each current file.

This slice does not complete issue17 or the general migration/readiness work. Cancellation discovery, legacy retry discovery and Work catalog/pending-journal scans remain separate performance concerns. Existing SQL stores are retained; consolidation and additional storage backends are outside this correction.
