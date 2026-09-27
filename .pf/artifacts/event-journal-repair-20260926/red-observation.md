# Reproduced unlocked append race

Before modifying append_process_event, the new actual four-process smoke was executed against the original source. It exited 1: `AssertionError: duplicate-id race: 3 copies` at the check requiring exactly one evt_shared. A barrier plus a 0.25-second first-read delay exposes simultaneous dedup reads. Existing seed bytes remained available and all worker subprocesses had exited normally before this assertion.

Command: `python -B tools/smoke_process_event_concurrency.py`. This reproduces duplicate id acceptance under concurrent writers; it does not prove the cause of the historical timestamp fragment. The subsequent source fix must pass the same unchanged concurrency test.
