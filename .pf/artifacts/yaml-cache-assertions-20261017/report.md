# Qualified test correction

Four snapshot-composition smokes now correctly expect cross-request shared YAML parse reuse. No product/cache behavior changed. Existing live-byte, same-size/mtime mutation, caller-copy isolation, request cleanup and error assertions remain.

All four scripts / 29 cases passed. Source commit: 69b2fa0a25ab9821000aaa069bff3fe439b86a1c. Both origin/dev and gitverse/dev were read back at that SHA; GitVerse used the existing token without a browser. Detailed checks and publication receipt are retained here.

The active Garage hook delivery owns checksum regeneration, full-suite reconciliation, final archive/build, installation and actual Runtime validation. This narrow source correction does not independently qualify an installed device or connected MCP host. It is handed to that delivery as an exact committed dependency.
