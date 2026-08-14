# Runtime temporary workspace matrix

## Scope

Executed `runtime-temp-matrix.py` on 2026-08-14 from `D:\Dev\process-forge`.
The probe used five creation APIs for each root and, within each isolated
generated directory, verified child creation, UTF-8 file write/read, rename,
and deletion. It did not touch a production workplace or Runtime code.

## Result

All 25 combinations passed:

| Root | TemporaryDirectory | mkdtemp | os.makedirs | Path.mkdir | PowerShell New-Item |
| --- | --- | --- | --- | --- | --- |
| System TEMP (`C:\Users\musst\AppData\Local\Temp`) | PASS | PASS | PASS | PASS | PASS |
| `.pf/runtime/test-temp` | PASS | PASS | PASS | PASS | PASS |
| `.tmp` | PASS | PASS | PASS | PASS | PASS |
| user LocalAppData | PASS | PASS | PASS | PASS | PASS |
| explicit `D:\Dev\process-forge` root | PASS | PASS | PASS | PASS | PASS |

Raw machine-readable evidence is `runtime-temp-matrix-results.json`.

## Interpretation

The historical `PermissionError [WinError 5]` is **not reproduced in this
session**. The current system temporary root resolves to the user-local C:
temporary directory rather than the historical `D:\Temp`; basic ACL and
filesystem operations are therefore presently available.

This does not establish the historical root cause. It rules out treating the
old report alone as evidence of a current product portability defect, and it
does not justify a test-only temp-root workaround. The next evidence step is
the unmodified `smoke_long_lived_runtime.py` under the current default
environment; if it fails, its complete first failing operation becomes the
subject of diagnosis.

## Shell-worker verification

The assigned `gpt-5.3-codex-spark` worker returned exit code 0 and wrote its
expected report, but did not create the promised matrix script and provided no
raw execution evidence. Its conclusion was not accepted as proof. This probe
was created and run independently.
