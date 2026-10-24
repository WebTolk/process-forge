# Device delivery verification cases

| Case | Actual evidence | Result |
| --- | --- | --- |
| Qualified dev alias byte identity | dev-package.json | PASS; same ZIP, only sidecar archive filename differs semantically |
| Native plan, no locally modified managed files | update-plan.json | PASS; 3 added, 21 changed, 1476 unchanged |
| One native apply and verified backup/control | apply.json; installed-verification.json | PASS; 21 backup preimages, all 1500 managed hashes |
| Preserve configuration, unknown files, index and unrelated source | installed-verification.json; live-installed-checks.json | PASS |
| Physical installed owner/imports and CLI independent of source cwd | physical-installed-identity.json | PASS |
| Physical strict context and exact scoped material | live-installed-checks.json | PASS; existing fresh snapshot, complete scoped coverage |
| Full registered tests on verified installed-payload copy | installed-pytest.json | PASS; 858/7 existing skips/383 subtests |
| Targeted Runtime/MCP/monitor/CLI native fixture smokes | installed-native-smokes.json | PASS; 8/8 |
| Real Runtime restart and loaded alpha5 identity | server-restart.json | PENDING; native guarded 409 refusal, no force |
| Real connected-MCP loaded alpha5 identity | connected-mcp-boundary.json | PENDING; genuine client reconnect required |
| Exact resumption checkpoint | native continuation alpha5-device-process-acceptance-20261024 | READY; all expected files present; actual process gates still open |

Native channel validation by the physical installed alpha5 CLI is separately
recorded in source revision/metadata-delivery.json after all installed hashes
were reverified. No fixture acceptance is promoted to actual service acceptance.
