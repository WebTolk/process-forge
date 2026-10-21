# Execution Context Summary

## Project
- process-forge @ `D:\dev\process-forge`
- PF context: fresh (snapshot_id: ctx-20261021-162229-c46ea2)
- Process: software-feature-development v1.2.1
- Assignment: processforge-pf-outbox-2
- Run: garage-processforge-pf-outbox-2

## Resources Authorized
- docs.python:root
- docs.python-packaging:root
- docs.python-practices:root
- docs.python-devguide:root
- docs.python-peps:root
- project.process-forge:project-profile
- project.process-forge:project-artifacts

## Tools Available
- PF MCP/CLI (`tools/processforge.py`)
- Python 3.14.3
- pytest, ruff, mypy (project toolchain)

## Audit Surface
- PF-managed artifacts, assignments, runs, handoffs, logs.
- Hook configuration (`.pf/hooks.yaml`) and outbox directory.
- Hook delivery code path in Core and Runtime tools.
