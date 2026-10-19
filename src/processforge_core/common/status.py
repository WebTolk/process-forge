from __future__ import annotations


def aggregate_status(statuses: list[str]) -> str:
    normalized = [status for status in statuses if status]
    if not normalized:
        return "SKIP"
    if "FAIL" in normalized:
        return "FAIL"
    if "WARN" in normalized:
        return "WARN"
    if all(status == "SKIP" for status in normalized):
        return "SKIP"
    return "PASS"
