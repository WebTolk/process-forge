# T05 independent review follow-up

I rechecked the current source after the fixes to the findings in `review-initial.md`. All four review blockers are resolved in source:

1. Governed collection now records receipt/event evidence without invoking compatibility `task-complete`; legacy task batches retain that path (`tools/processforge.py:19342-19355`).
2. `local_file` rejects redirected path components, and the lifecycle lock preflights every fixed worker-run path before worker operations (`src/processforge_core/prepared_input.py:32-43`, `tools/processforge.py:18548-18562`). Prepared input, receipt, and completion files use atomic no-clobber publication (`prepared_input.py:144-160`).
3. Collection validates report size/UTF-8 before receipt creation, then checks the receipt's raw report checksum (`tools/processforge.py:19282-19298`).
4. Prepared Codex payloads now use fixed instructions plus the verified prepared manifest; only the legacy direct CLI path reads the mutable worker prompt, capsule body, or workspace-access pointer (`tools/codex_exec_worker.py:114-139`).

The latest source review found no remaining concrete blocker in the scoped T05 surfaces. I did not run tests or claim runtime/developer-probe acceptance; those remain with the primary/test engineer.
