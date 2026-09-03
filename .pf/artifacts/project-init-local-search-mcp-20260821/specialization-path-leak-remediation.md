# Specialization public-path remediation

Status: implemented and regression-covered by the clean initialization fixture.

Selected workplace specializations are resolved from private workplace paths.
The snapshot producer formerly copied such an absolute manifest path into
public `selected_specializations[].path`. It now emits the stable private
marker `<private-specialization-ref>` for an out-of-project specialization and
keeps a relative path only for a project-local specialization.

Runtime continues to resolve the actual specialization through its authorized
workplace registry; public context snapshots no longer disclose the workplace
location.
