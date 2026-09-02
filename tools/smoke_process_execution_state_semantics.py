#!/usr/bin/env python3
"""Acceptance coverage for incomplete versus blocked declarative work."""

from process_execution_smoke_support import scenario


if __name__ == "__main__":
    scenario("state_incomplete_not_blocked")
    scenario("blocked_state_is_distinct")
    scenario("blocks_missing_gate")
    print("PASS: work state distinguishes incomplete requirements from blocked work")
