#!/usr/bin/env python3
"""Smoke the focused core hardcode policy against runtime and core resources."""

from smoke_domain_neutral_core_helpers import ROOT, load_processforge


def main() -> None:
    pf = load_processforge()
    from processforge_core.maintenance.public_source_checks import PublicSourcePolicy
    from processforge_core.work.context_documents import ContextContractInputs

    violations = PublicSourcePolicy(Path(__file__).resolve().parents[1], inputs=ContextContractInputs()).core_hardcode_violations(ROOT)
    if violations:
        raise AssertionError(violations)
    print("PASS: smoke_runtime_no_domain_file_patterns")


if __name__ == "__main__":
    main()
