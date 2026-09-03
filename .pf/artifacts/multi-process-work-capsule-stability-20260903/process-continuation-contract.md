# Process continuation contract

Status: ready_for_review

Stage transition remains an intra-Work move. Process transition is a completed-Work boundary:

```text
Run A (architecture-analysis) -> handoff -> Run B (software-feature-development)
```

Run B receives a new process pin, capsule, specialization set and effective resource set. Run A remains historical and is represented to a future session through a compact handoff/summary, not by injecting its full prior process context.

The result may offer available and recommended next process ids plus a non-binding session-continuity recommendation. It does not auto-start Run B and does not impose Runtime, Ledger, hooks, or a fresh external session.
