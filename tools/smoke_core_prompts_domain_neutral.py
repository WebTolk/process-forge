#!/usr/bin/env python3
"""Smoke that root core prompts do not expose domain workflow companions."""

from smoke_domain_neutral_core_helpers import DOMAIN_CORE_PROCESS_IDS, ROOT


def main() -> None:
    prompt_root = ROOT / "prompts"
    violations = [
        process_id
        for process_id in DOMAIN_CORE_PROCESS_IDS
        if (prompt_root / f"{process_id}-agent.md").exists()
    ]
    if violations:
        raise AssertionError(violations)
    print("PASS: smoke_core_prompts_domain_neutral")


if __name__ == "__main__":
    main()
