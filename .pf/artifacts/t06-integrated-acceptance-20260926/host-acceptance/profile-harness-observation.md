# Harness observation

The first profile loop recorded passing quiet/normal cases, then stopped before diagnostic calls because it treated an exec_command response without exit_code (still running) as a command failure. Fixture configuration was written successfully; no product failure was observed. The corrected loop polls a returned session_id to completion and resumes only the remaining profiles, preserving prior results.
