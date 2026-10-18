# Managed egress engine

T07 provides an explicit Windows HTTP/JSON broker for a remote recipient. It
mediates the initial envelope, subsequent resource reads, trusted tool results
and derivative exports. Native Codex CLI, generic shell and isolated-local
execution have **no strict capability**. They cannot silently substitute for
`mediated_session`. This broker is a finite protocol, not an adapter for an
arbitrary vendor's chat API or a sandbox for arbitrary local programs.

## Operator flow

1. Create a trusted local policy JSON using the fields below. Inspect each whole
   source and record its `sha256:` checksum. A source becomes public only by
   that declaration; absence of a detector finding is insufficient.
2. Run `pf egress bind --policy <policy.json>` and save the JSON result as a new
   intent file. For a successor add `--project-root <project> --predecessor <id>`.
3. Run `pf work-start --project-root <project> --objective <new-portable-objective>
   --process-id <allowed-process> --egress-intent <intent.json> --json`.
   The service seals v2 before writing lifecycle records. It refuses to resume
   a same-objective Work with different security intent. Historical v1 files
   remain unchanged; a new objective identifies a separate successor Work.
4. Choose an existing external parent directory and use its
   `.pf-egress-private` child as `<store>`. Run `pf egress qualify --project-root
   <project> --store-root <store>`. Qualification runs synthetic Windows/Work/TLS
   tests; it requires Python, the Core dependencies and OpenSSL (including the
   copy shipped with Git for Windows). It sends no project data. Qualification
   is invalidated by Core/code/Python/OS changes; repeat it after an update.
5. Run `pf egress run --project-root <project> --assignment <id> --attempt 1
   --policy <policy.json> --store-root <store>`. Each attempt number is used
   once. The result is a JSON receipt, with optional filtered result text.
   `--credential-file <owner-only-file>` supplies only HTTP authentication.

`egress status` reports local qualification. `egress revoke --policy <policy>`
permanently denies that binding in the same store. All participating operator
commands must use the same store; creating a different trusted store is an
operator trust/configuration change, not a way for a model to reset its budget.
The revocation and send paths share a nonblocking process lock; `egress_busy`
means the revocation was **not** applied and must be retried by the operator.

`egress export` takes the same Work/policy/attempt/store arguments plus
`--output <new-file>`. It creates a sanitized derivative, never replaces a file
and never repairs or relabels an original capsule/doctor result. Export consumes
a disclosure reservation. The private receipt links derivative and original
checksums; exported bytes contain only random references and approved content.

## Policy shape

Required top-level fields:

| Field | Contract |
| --- | --- |
| `schema_version`, `id` | `1`, stable policy id |
| `recipient` | `id`, `purpose`, exact `endpoint`, `transport` |
| `limits` | Every limit listed below; values can only lower the ceilings |
| `sources` | Project-relative filename to source declaration, at most 128 |
| `denied_sources` | Exact paths; denial wins before a read or transformation |
| `redact_classes` | Explicit classes eligible for whole-unit replacement/omission |
| `exceptions` | Exact benign-byte review exceptions; empty list by default |
| `tools` | Finite allowed tool ids, e.g. `text-stats`; empty list denies tools |

Each source declares `classification` (`public`, `internal`, `restricted`,
`personal`, `secret`, `credential`, `unknown`), `checksum`, `format` (`text` or
`json`), boolean `required` and `initial`, and `transform` (`none`, `redact`,
`omit`). Required sensitive content blocks with `required_semantics_lost`.
An optional block is replaced or omitted only when explicitly permitted.
Unknown classification, unsupported binary/encoding, duplicate JSON keys and
unscanned tails block. Whole-unit replacement deliberately does not promise to
preserve useful fragments of a sensitive instruction.

An exception has `checksum`, `detector`, `recipient`, `purpose` and Unix-seconds
`expires`. Only review detectors (email, private path, opaque encoding, raw
digest) are eligible. Strong credential/private-key/synthetic-secret findings,
declared secrets, scope and locked/current denials cannot be exempted.
Detectors are a finite conservative bundle, not a universal secret recognizer.
Correct source declarations remain necessary. Corpus measurements are reported
by qualification and are not a security guarantee or performance SLA.

Optional `result` declares `classification`, `format: text`, `required` and
`transform` for final recipient text. Without it the recipient may only finish
without text. Tool implementations are trusted local code. The shipped CLI
registers only the pure `text-stats` tool with one string argument `text`.
Python integrations registering additional tools must bind every tool's
fingerprint in policy `tool_bindings` and separately grant its effect. The
effect must also be allowed by Work (except pure computation); a Work action
denial always wins, including for pure tools. Tool policy cannot widen Work.
The
fingerprint covers arguments, code, declared effect/result rule and credential
channel. A model cannot import a tool or grant an effect. Trusted tool code
itself and its dependencies must be reviewed; the engine is not their OS sandbox.

## Wire protocol and limits

Requests are exactly the approved UTF-8 JSON view:

```json
{"protocol":"pf.egress/1","resources":["opaque-handle"],"tools":["text-stats"],"items":[{"ref":"opaque-handle","status":"allow","text":"Approved text"}]}
```

The server returns one JSON operation with exactly the declared fields:

```json
{"op":"read","handle":"opaque-handle"}
{"op":"tool","name":"text-stats","arguments":{"text":"Literal text"}}
{"op":"finish"}
{"op":"finish","text":"Result text, only when policy declares result"}
```

There is no path, environment, home, plugin, child-process, arbitrary-URL,
range-read or policy-edit operation. Resource handles have meaning only inside
their owning live attempt. Placeholder strings stay literal. Every source is
authorized before opening and checked in full before classification; approved
bytes are immutable. A changed source, actual path, Work stage, policy, route,
tool or qualification invalidates the operation.

Ceilings: `unit_bytes: 1048576`, `envelope_bytes: 4194304`,
`attempt_bytes: 33554432`, `disclosures: 128`, `json_depth: 16`,
`classification_ms: 2000`, `token_seconds: 30`. The attempt also bounds source
bytes read for revalidation. Tokens use a monotonic clock and cannot survive a
restart. Preparation is bounded before assembling a large envelope.

`https-json-v1` uses Windows certificate stores and hostname verification,
without ambient proxy, TLS key-log or trust-file environment settings.
`loopback-json-v1` permits only numeric loopback HTTP for explicit local fixtures;
it never means `isolated_local`. Requests have fixed framing and no redirects,
SDK additions, retry, streaming or telemetry. Responses require a finite length,
JSON content type and no transfer/content encoding. Socket connection/handshake
timeouts and a whole-response deadline bound network operations; OS DNS latency
is not claimed as a hard real-time guarantee.

## Audit and recovery boundary

Windows creates the private directory with a protected owner-only ACL before
writing content. Files inherit that ACL and it is rechecked before use. The
reserved component is excluded from Work resource material even if an ancestor
is registered. Only this Windows route is qualified. Same-account malicious
code, administrators, Core tampering and separately retained backups remain
outside the boundary.

Before send, Core durably records the reservation and mandatory audit receipt.
Optional diagnostics can fail independently. If bytes may have left and a final
receipt is absent, the result is `delivery_unknown`. There is no automatic
resend or refund; a failed/used view cannot be authorized again. `egress_busy`
and other pre-send denials send no new envelope. Views, reverse maps and tokens
are attempt-local memory. Closing invalidates handles immediately. `egress prune`
deletes only receipt bodies older than 30 days; opaque budget/replay tombstones
remain. This is retention, not a claim of cryptographic erasure.

Source tests, archive tests, installed qualification and a connected capturing
recipient are separate evidence. A successful local broker qualification does
not prove that a separately connected host MCP or native assistant is mediated.
