"""Existing pure Work permission readiness shared by lifecycle and Continuation."""

def permission_readiness(scope: dict, mode: dict) -> dict:
    actions = set(scope.get("allowed_actions") or []) - set(scope.get("forbidden_actions") or [])
    reads = scope.get("allowed_read_files") or scope.get("allowed_files") or []
    writes = scope.get("allowed_files") or []
    reasons = []
    if "read" not in actions or not reads:
        reasons.append("read_scope_missing")
    if mode.get("code_changes_allowed") and ("write_product" not in actions or not writes):
        reasons.append("product_write_scope_missing")
    if mode.get("kind") != "read_only" and mode.get("artifact_changes_allowed") and (not writes or not actions & {"write_product", "write_artifact"}):
        reasons.append("artifact_write_scope_missing")
    return {"status": "blocked" if reasons else "ready", "blockers": reasons,
            "allowed_actions": sorted(actions), "allowed_files": writes,
            "allowed_read_files": scope.get("allowed_read_files") or [],
            "remediation": "create_explicitly_scoped_successor" if reasons else "none"}

