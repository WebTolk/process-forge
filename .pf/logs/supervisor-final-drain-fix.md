# Supervisor Final Drain Fix Log

## 2026-07-25 - implementation

- agent/role: main Codex agent
- task: implement `задания/processforge_supervisor_final_drain_detached_state_master_prompt.md`
- files analyzed: `tools/processforge.py`, `tools/smoke_process_supervisor_lifecycle.py`, `tools/smoke_full_shell_agents_supervisor.py`, runtime driver docs, release-test registry
- files changed: `tools/processforge.py`, `tools/smoke_supervisor_final_drain.py`, `tools/smoke_full_shell_agents_supervisor.py`, validation registries, supervisor docs, `.pf` evidence artifacts
- status: implementation complete; targeted smoke validation in progress
- follow-up items: refresh checksum inventory, run full public release tests, rebuild and validate `dist/processforge.zip`
- tooling gaps: Serena symbol extraction unavailable because active languages were empty; used targeted shell reads and `apply_patch`

## 2026-07-25 - validation

- agent/role: main Codex agent
- task: targeted and full public validation for supervisor final drain
- files changed or analyzed: `tools/processforge.py`, `tools/smoke_supervisor_final_drain.py`, `tools/smoke_full_shell_agents_supervisor.py`, release-test reports under `.pf/runtime`
- status: targeted smokes and full public release tests passed
- verification: `python bin/pf.py release-test --root . --only smoke_supervisor_final_drain --public --fail-fast --timeout-scale 1` passed in 11.80s
- verification: `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1` passed in 218.20s
- verification: `python bin/pf.py release-test --root . --public --timeout-scale 1` passed in 224.02s
- follow-up items: refresh checksum inventory after evidence updates, rebuild archive, run full extracted archive test
- residual risks: none known for the targeted final-drain contract

## 2026-07-25 - extracted archive race follow-up

- agent/role: main Codex agent
- task: stabilize one-tick detached PID visibility race found during clean extracted archive proof
- files changed or analyzed: `tools/processforge.py`, `tools/smoke_full_shell_agents_supervisor.py`, extracted archive smoke output
- status: fixed by requiring a second lost observation before `unknown_exit` when `exit.json` is absent
- verification: `python -m py_compile tools/processforge.py tools/smoke_supervisor_final_drain.py tools/smoke_full_shell_agents_supervisor.py` passed
- verification: `python -u tools/smoke_supervisor_final_drain.py` passed
- verification: `python tools/smoke_full_shell_agents_supervisor.py` passed
- verification: `python tools/smoke_process_supervisor_lifecycle.py` passed
- verification: `python bin/pf.py release-test --root . --only smoke_supervisor_final_drain --public --fail-fast --timeout-scale 1` passed in 11.87s
- verification: `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1` passed in 227.19s
- verification: `python bin/pf.py release-test --root . --public --timeout-scale 1` passed in 223.87s
- verification: `python bin/pf.py release-pack --root . --output dist/processforge.zip` wrote 458 files
- verification: `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1` passed; extracted archive release-test took 225.99s
- follow-up items: none

## 2026-07-25 - smoke process supervisor semantics follow-up

- agent/role: main Codex agent
- task: stabilize `tools/smoke_process_supervisor.py` and remove timing assumptions from the public release-test path
- files changed or analyzed: `tools/smoke_process_supervisor.py`, `docs/concepts/process-supervisor.md`, `.pf/artifacts/checksum-inventory.sha256`
- status: implemented
- contract clarification: first supervisor run with `--max-ticks 1 --interval 0` now checks only final-drain observe/collect and no-new-start semantics; dependent-chain completion is checked by a bounded run-to-stable helper that allows later scheduling passes
- verification: `python -m py_compile tools/smoke_process_supervisor.py tools/processforge.py` passed
- verification: `python tools/smoke_process_supervisor.py` passed
- verification: `python tools/smoke_supervisor_final_drain.py` passed
- verification: `python bin/pf.py release-test --root . --only smoke_process_supervisor --public --fail-fast --timeout-scale 1` passed
- verification: `python tools/validate-process-forge-checksums.py --root . --check` passed
- verification: `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1` passed in 296.66s
- follow-up items: rebuild `dist/processforge.zip` and validate archive freshness
