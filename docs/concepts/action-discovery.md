# Supported Actions And Native MCP Operations

Use discovery before guessing a PF operation or copying an option from another
command. The catalogue describes the CLI parser and MCP registry loaded by the
running distribution. A supported operation still requires its native guards,
current permissions, valid inputs and applicable process state.

```bash
python bin/pf.py actions list --query worker --surface cli --limit 10 --json
python bin/pf.py actions describe --action-id "cli:worker-run prepare" --json
python bin/pf.py actions describe --action-id "mcp:pf.work.start" --json
```

CLI identifiers use `cli:<actual command path>`; MCP identifiers use
`mcp:<advertised tool name>`. CLI aliases remain distinct real routes. List
returns a deterministic, bounded page. Describe returns the selected operation's
argument/schema details. Unsupported IDs are reported explicitly and are never
dispatched as a guessed substitute.

`pf.actions.list` accepts `query`, `surface` (`cli` or `mcp`), `limit` (1–100,
default 25) and nonnegative `offset`. `pf.actions.describe` requires `action_id`.
Both follow normal project/session binding and support optional exact
`run_id`, `assignment_id`, `context_id`. Supply all three selectors together.
Without selectors, discovery does not choose a current/latest Work or assert
permission to execute an action. With selectors, it uses the current explicit
Work projection. Native validation remains authoritative.

The catalogue is built from actual registrations rather than a second handwritten
inventory of hundreds of commands. It preserves declared flags, choices,
requiredness and aliases. Runtime/private defaults and callable objects are not
published as portable defaults. Undeclared result contracts, native validators
or effects remain unknown rather than being inferred from an operation's name.

Version and catalogue/schema fingerprints identify the reported metadata.
A matching fingerprint does not establish loaded implementation parity, an
installed update, or acceptance through an application's connected MCP process.
An already running MCP process can retain an older catalogue after files on disk
change. Compare advertised tools and fresh connected requests after the normal
host reconnect before claiming connected-host qualification.

## Curated MCP Operations

The additional tools expose existing native functionality. They do not provide
an arbitrary command executor, executable override or a new permission model.

| Tool | Main inputs and behavior |
| --- | --- |
| `pf.actions.list` | Filter and page supported CLI/MCP metadata. No execution. |
| `pf.actions.describe` | Describe an exact `action_id`. No execution. |
| `pf.runtime_driver.list` | Registered driver IDs and status for the project/workplace. |
| `pf.runtime_driver.describe` | Required registered `driver` ID; safe metadata without command/environment values. |
| `pf.worker.prepare` | Exact Work selectors, explicit registered `driver`, `apply: true`; native scope/input preparation. |
| `pf.worker.start` | Same identity/driver requirements, `apply: true`; native launch always detaches and returns immediately. |
| `pf.worker.status` | Exact Work selectors and `apply: true`; native observation may reconcile records and collect completed output. |
| `pf.worker.collect` | Exact Work selectors and `apply: true`; native report/hash/attempt collection checks. |
| `pf.session.heartbeat` | `apply: true`; renew the existing bound Ledger session. No `ttl` argument or registration. |
| `pf.chat.record` | Required `content`, `apply: true`; assistant message attributed to the bound Ledger agent in its own session transcript. |

Worker prepare/start optionally accept `model` and `reasoning_effort`
(`minimal`, `low`, `medium`, `high`). Driver IDs must already be registered;
manifest paths and executable overrides are outside this MCP subset. Existing
native CLI options remain available through their own described CLI routes.
There is no MCP `wait`, arbitrary participant/role or chat target override.
The facade selects a manifest from the registry by exact ID and passes that
selected reference to native commands, avoiding same-name file fallback. A
missing registered manifest is refused. A bound session also requires
the same canonical project directory; matching project IDs alone are insufficient.

```json
{
  "project_root": "<project-root>",
  "run_id": "<returned-run-id>",
  "assignment_id": "<returned-assignment-id>",
  "context_id": "<returned-context-id>",
  "driver": "codex-exec",
  "apply": true
}
```

This is an input example for `pf.worker.start`, not permission to launch.
Use the identity returned by PF and the driver's configured model policy.
The facade rejects terminal governed Work before prepare/start/collect and
delegates to the existing native CLI application, including invocation checks.
Native implementations retain locks, prepared-input verification and collection
authority. A successful detached launch or provider exit is not parent Work
acceptance; read the report and integrate evidence before transitioning.

`pf.worker.status` is intentionally not annotated read-only. `pf.worker.start`
can execute a configured external driver and is annotated as open-world.
Heartbeat/chat require an existing Ledger-bound session and project match;
the tool cannot manufacture a missing session. Conversation channels managed
through other existing native CLI operations are not implicitly exposed by this
bounded session transcript route.

Declared schema limits are enforced before business dispatch, including array
cardinality, string lengths, unknown fields, numeric limits and exact JSON types.
Discovery does not bypass those checks or broaden a worker's file/resource scope.

See [Runtime MCP](runtime-mcp.md), [prepared inputs](prepared-input.md),
[Work contract](work-execution-contract.md) and
[Python Core ownership](python-core-structure.md).
