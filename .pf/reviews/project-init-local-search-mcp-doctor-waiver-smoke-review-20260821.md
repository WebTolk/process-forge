# doctor-waiver-smoke-review

## Result

Accepted with an execution-environment caveat.

The narrowed smoke contract in `tools/smoke_doctor_project_capability_waiver.py` still proves the requested three behaviors by direct assertions:

1. blocked `project-init` when required capabilities are unresolved;
2. unwaived `doctor-project` failure for missing capability registry declarations;
3. successful `doctor-project` after explicit runtime-access waivers are added.

## Findings

No product-code findings in the reviewed scope.

## Evidence

- `tools/smoke_doctor_project_capability_waiver.py:58-62` runs `project-init --apply` against an isolated fixture and asserts both `status: blocked` and `doctor:\n  status: fail`.
- `tools/smoke_doctor_project_capability_waiver.py:64-68` runs `doctor-project` before waivers, requires a non-zero exit, and asserts the missing registry declaration diagnostic.
- `tools/smoke_doctor_project_capability_waiver.py:70-93` writes `.pf/artifacts/capability-waivers.yaml` for both required capabilities with `status: active` and evidence fields.
- `tools/smoke_doctor_project_capability_waiver.py:94-98` reruns `doctor-project`, requires exit code `0`, and asserts the explicit runtime-access waiver diagnostic.
- `tools/processforge.py:7532-7564` loads active waivers from `.pf/capability-waivers.yaml` and `.pf/artifacts/capability-waivers.yaml`, accepting `active`, `waived`, or `verified` records and ignoring expired records.
- `tools/processforge.py:20247-20267` splits missing required capabilities into unwaived and waived sets; unwaived capabilities produce `FAIL`, while fully waived missing capabilities produce only `WARN`.
- `tools/processforge.py:2663-2668` makes `doctor-project` return non-zero only on `FAIL`, so the all-waived `WARN` path is a successful doctor run.
- `tools/processforge.py:6720` registers `smoke_doctor_project_capability_waiver` in the release command list.

## Runtime Check

Attempted command:

```powershell
python tools/smoke_doctor_project_capability_waiver.py
```

Result: not completed. The read-only worker environment failed before any product assertions, while creating the temporary fixture directory:

```text
PermissionError [WinError 5]: D:\temp\pf-cap-waiver-...\project
```

This is consistent with the current assignment filesystem profile and is not evidence of a ProcessForge contract failure.

## Conclusion

The narrowed smoke is correctly scoped and still covers the intended doctor waiver behavior. Full runtime acceptance still requires rerunning the smoke in a writable temp environment and getting the terminal `PASS: smoke_doctor_project_capability_waiver` result.