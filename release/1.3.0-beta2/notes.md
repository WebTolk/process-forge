# ProcessForge 1.3.0-beta2

This beta repairs context and process catalog reads when private YAML processes
are stored under the installation's `processes/user/` or `processes/custom/`.
These definitions remain project or workplace data and stay out of the public
Core manifest and ZIP. Existing process IDs and catalog precedence are unchanged.

Only read access to unpublished YAML/YML uses this private data boundary.
Published payload still comes from its accepted byte image. Code files, writes,
path aliases, links and files changed during capture remain refused.

Owned temporary cleanup also compares identities in one Python representation
on the pinned Windows handle. This fixes false identity-change refusals on
Python 3.11 without truncating file IDs or relaxing ownership checks. The
worker input capture and conversation smoke use their current provider-adapter
owner.

This is an isolated successor to beta1. Other pending development changes are
not included. Focused repair qualification does not establish general Core,
POSIX, RC or stable-release acceptance; stable remains 1.2.0.
