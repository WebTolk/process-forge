# Test report

2026-10-22. PASS. Final qualified candidate and exact commands/exits/hashes are in qa-verified.json; final logs have the -verified suffix. Python 3.14.3, pytest 9.1.1.

The registered pytest launcher ran tests/kimi_hooks and tests/project_hooks/test_agent_hooks.py: 85 passed, 13 subtests passed, exit 0. Existing smoke_provider_adapter_admission.py passed, exit 0. These exercise real source ingress and isolated direct script execution, with synthetic native-shaped events.

All 78 preservation-baseline files retain their original live hashes. Earlier intermediate failed QA logs are retained for traceability and are superseded by the final verified results. No full release/archive/device/model acceptance is claimed here; the user's new dev-device request is handled in a separate governed scope.
