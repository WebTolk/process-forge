# Operational assurance

Primary review passed. No product code changed and no new product test suite is needed. Delegation is forbidden by capsule; no independent/subagent review is claimed.

Validation plan and actual cases:

- Identify service using runtime.lock, instance ID, actual process and authenticated lifecycle. Before: PID 13540 / instance 84c60b0dd3df4740aaf1f18d3e9cce2c. After: PID 16976 / instance 7e99504388824711a0e0c38b5fa400cf. Old owner/launcher are absent; new owner uses installed processforge.py runtime serve. Separate MCP PID 5284 retains its creation identity.
- Verify only the managed CLI was used. Two earlier normal attempts returned guarded 409. User then explicitly authorized the requested --force. Installed CLI returned exit 0; new readyz reports ready=true. No OS kill, lock cleanup, product update or unrelated repair occurred.
- Pin Windows process handles and creation FILETIME across each interval. Record monotonic wall time and user+kernel CPU deltas; normalize by the four logical CPUs. Recomputed totals agree with stored aggregate percentages within 0.002 percentage points. All samplers exited 0.
- Separate measured windows: before 30.001 s at 21.8876%; first post-start sample 30.000 s at 21.4189%; following 60.001 s at 20.7354%, max 26.9430%, median 24.21155%. First post-start sample starts around 20 seconds after process creation. Do not describe it as the first 30 seconds since creation.
- Do not perturb the settled sample with PF control calls. MCP CPU delta stayed zero throughout both post-start windows. These are actual background observations, not a standardized capacity benchmark.
- Report actual readiness and health separately. Service is ready/degraded with existing scheduler failures. Installed VERSION remains 1.2.0; installed journal/service hashes differ from source SQLite implementation. Restart-only does not qualify deployment of that fix.

Evidence: before-cpu.json, startup-cpu.json, settled-cpu.json, cpu-summary.json, force-authorization.md, force-restart-command.json, new-owner.json, after-processes.json, after-state.json, installed-provenance.json, retained sample_cpu.py and report.md. Task scope respected and no operator action remains for the requested single restart/measurement.
