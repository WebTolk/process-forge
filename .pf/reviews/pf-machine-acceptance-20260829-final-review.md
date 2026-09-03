# Final Restoration Review

Result: `pass_with_conditions`.

## Restored Installation

- Standard rollback update: `core-update-20260829T110033Z`.
- Transition: installed `1.2.1` to original archive `1.1.0`.
- Plan/apply counts: changed 193, removed 25, unchanged 675, local modifications 0, missing owned 0, blockers 0.
- Manifest owns 868 files; direct SHA-256 verification found missing 0 and mismatch 0.
- Manifest SHA-256: `d710b331dae0fa0625934e46b886cb606a4824290bf50e65b57ad58d86015b75`.
- Original archive SHA-256: `fd4c9948de1270a2b836c19796b6882ab994ec61dde854a44403f949661f43dc`.
- Approved `.codex/hooks.json` was preserved; SHA-256 `0107fce9df4e63ce8024d6416fb5f546b47b421825c2e3a12924fa4f980bfd9c`.

## Services

- Runtime restarted from restored 1.1.0: PID `10404`, endpoint `http://127.0.0.1:57772`.
- `/readyz` returns `ready=true`, `status=ready`; protocol, core version, token, lock, cache and ledger doctor checks pass.
- Runtime status remains `health=degraded`, and scheduler `tick` times out. This is the reproduced 1.1.0 defect fixed and tested in candidate 1.2.1, not restoration drift.
- Standalone hidden MCP is running through `py.exe` PID `10680`, Python child PID `13356`, using the restored installed server and workplace.
- No candidate release-test or governed worker process is left running.

## Acceptance Result

The local unpublished 1.2.1 candidate passed full extracted-archive qualification, target-side update/rollback, installed PF-first MCP worker, native hooks, telemetry/chat capture and real Joomla plugin behavior. The machine has been returned to exact managed-file parity with 1.1.0 while preserving workplace, Joomla project and hook state.

Conditions: Spark quota and browser backend were unavailable; Joomla search supplied authoritative paths but no narrow content-plugin article; restored 1.1.0 retains its known scheduler timeout.
