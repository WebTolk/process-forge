# f12-ingress-report

## Result

Implemented bounded raw-ingress recovery and added the focused smoke test.

## Design

- Added atomic per-shard byte-offset checkpoints.
- Normal cache misses no longer scan historical records.
- Recovery scans only unindexed durable tails.
- Missing checkpoints trigger one-time legacy migration.
- Malformed indexes are rebuilt; corrupt/truncated journals fail closed.
- Existing lock ownership is unchanged.

## Verification

`py_compile` completed successfully.

Smoke command attempted:

```text
python tools/smoke_raw_ingress_incremental_recovery.py
```

It was blocked by the assignment’s sandbox condition: temporary-directory creation under `C:\Users\musst\AppData\Local\Temp` failed with `PermissionError: [WinError 5]`. No ACL investigation or retry was performed.

The smoke now supports:

```text
python tools/smoke_raw_ingress_incremental_recovery.py --root <writable-scratch-root>
```

Primary-agent execution is still required for dynamic verification.