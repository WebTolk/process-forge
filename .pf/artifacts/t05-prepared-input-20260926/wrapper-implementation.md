# T05 provider-neutral executor wrapper handoff

Status: implementation complete for the isolated wrapper assignment. Product file: `tools/prepared_executor.py`.

## CLI and validation

Invocation shape is `python tools/prepared_executor.py --prepared-input <file> --prepared-sha256 sha256:<64 lowercase hex> --heartbeat <path> --exit-path <path> -- <target> [args...]`.

The wrapper requires an explicit `--` separator and nonempty target argv. It validates the prepared-input path against `PF_PREPARED_INPUT_FILE`, the supplied digest against `PF_PREPARED_INPUT_SHA256`, reads no more than 4 MiB plus one sentinel byte, hashes the raw bytes, decodes UTF-8 JSON, and requires integer `schema_version: 1` with `kind: pf.prepared-input`. The manifest must contain string project/run/assignment/context identity values, attempt as a string or integer, and a private `project_root`. Run ID, assignment ID, and attempt must match `PF_WORKER_RUN_ID`, `PF_WORKER_TASK_ID`, and `PF_WORKER_ATTEMPT`; when `PF_PROJECT_ROOT` is present, the manifest root must resolve to it. Failures return nonzero before target start and write a bounded failed heartbeat/exit marker when output paths were parsed.

The child receives a list argv with `shell=False`, inherited stdin/stdout/stderr, current working directory, and current environment. No shell evaluation, PF import/bootstrap, MCP call, or network behavior is implemented. This wrapper does not assert OS-level sandboxing.

## Lifecycle evidence

Heartbeat and exit JSON use atomic replacement. The wrapper writes `starting`, emits `running` heartbeats on a two-second interval with a monotonic sequence, then writes `completed` or `failed`. Exit proof uses the existing Codex-compatible shape `{schema_version: 1, exit_code, status}`. A launch failure records code 127; invalid prepared input records code 125; interruption records code 130. The target's own exit code is returned and persisted. Error records use stable codes rather than exception text or private path output.

## Validation and limits

Ran `python -B -m py_compile tools/prepared_executor.py`: PASS. No functional smoke, product integration, review, PF transition, or runtime setup was performed, as requested. The main agent owns driver wiring and behavioral coverage.
