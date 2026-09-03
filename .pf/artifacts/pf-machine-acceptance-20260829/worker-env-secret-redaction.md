# Worker Environment Secret Redaction

Status: pass

## Finding

Worker-run prepare/start persisted the complete inherited host environment in
the durable private command.json. This included credential-bearing variables
and violated the ProcessForge no-secret persistence boundary.

## Remediation

- Durable command state now contains only ProcessForge-owned and explicitly
  configured environment entries.
- Host environment inheritance is materialized in memory immediately before
  subprocess.Popen.
- Existing launch behavior is preserved through environment_inherit.
- The generated command files from the failed attempts were removed before
  launching another worker.

## Verification

- python -m py_compile tools/processforge.py tools/smoke_worker_environment_secret_redaction.py
- python tools/smoke_worker_environment_secret_redaction.py
- Generated worker command state does not contain the inherited credential key.
- Two codex-exec Spark workers started successfully after the remediation.

## Residual Risk

Explicit literal environment values declared by a runtime driver remain part of
the durable driver/command contract. Runtime drivers must continue to use
references for credentials rather than literal secret values.
