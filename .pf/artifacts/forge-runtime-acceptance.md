# Forge Runtime Acceptance

Status: not completed in this slice

No Forge Runtime lifecycle/autostart code was changed. Existing Runtime checks
were not expanded as part of this implementation task.

Required future proof:

- mode `forge`, Runtime stopped -> explicit
  `forge_runtime_required_but_unavailable`;
- mode `forge`, Runtime running -> Ledger/Director/scheduler/maintenance
  healthy;
- Windows and Linux documented autostart path.
