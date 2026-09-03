# Specialization parameter-source path remediation

Status: implemented and verified.

`parameter_source_record()` now emits `<private-source-ref>` rather than an
absolute path whenever a private source lies outside the project and no more
specific display marker was supplied. This covers workplace specializations
which contribute `parameters` to a public project-context snapshot, while
preserving project-relative paths and the existing private Runtime resolver.

`tools/smoke_project_init_acceptance.py` gives its selected workplace
specialization a parameter, asserts the public snapshot contains no workplace
path, and asserts that its parameter source has the private marker. The full
acceptance fixture passed after this change.
