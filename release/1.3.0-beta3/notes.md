# ProcessForge 1.3.0-beta3 development build

The file update contract is restored for existing installations that have no
native enrollment. Extract the verified release into a separate directory and
run its `bin/pf.py core-update plan|apply` with the explicit installed Core root,
ZIP and, when applicable, Workplace root. `apply` still requires `--confirm`.
The installer must remain outside the replacement target; self replacement
without managed enrollment is refused.

This route freezes and verifies the archive, serializes cooperating file
updaters, preserves real preimages and the recovery journal, replaces only
manifest-owned files, verifies the payload and publishes the new manifest last.
Unknown private data and user/custom processes remain in place. A known
Workplace App Server must be stopped before replacement. Workplace migration
operations require their existing qualified maintenance route.

Any complete or partial native enrollment retains strict native replacement.
The file route does not create a native control, epoch, adoption or migration
authority, and its mutex does not attest retirement of every other interpreter.

For a known Windows App Server whose authenticated shutdown refuses, the
external release CLI supports explicit `server stop --force`. Recovery verifies
the current owner and retained process handle, including interpreter, command
line and creation identity, before stopping only that process. Ambiguous owner,
managed target, authentication failure or unavailable OS facts still refuse.
Normal shutdown behavior is unchanged. Reconnect existing MCP hosts separately
after updating their installed Core.

The development archive is an isolated repair. General Core assurance, POSIX,
RC and stable-release acceptance remain separate. Extensible maintenance
packages shared by Runtime and MCP are future architecture work.
