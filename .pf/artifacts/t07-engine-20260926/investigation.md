# I01 feasibility and current impact

Actual source/installed baseline: 347c6d9e, official update
core-update-20260926T191610Z. No T07 public product edits yet. Exact baseline
hashes and reserved file patterns are in baseline.json. Single-agent process;
Python symbol provider unavailable, targeted reads/AST fallback documented.

The actual prepared_executor.run_target preserves cwd/environment and calls
subprocess.Popen(target, shell=False, inherited stdio, env=current_env).
Shell=False is not an isolation boundary. feasibility.py exercised this real
wrapper with a valid synthetic prepared identity and a controlled Python probe.
All five bypasses succeeded: sibling synthetic home config, inherited synthetic
environment value, synthetic plugin, child Python and numeric loopback network.
No real secret/model/external recipient was used. native-feasibility.json binds
the evidence to wrapper hash, Python/Windows identity and durable fixture path.

Codex adapter source chooses configurable PF_CODEX_SANDBOX (default read-only),
constructs native CLI argv and inherits the environment. Codex itself was not
executed or qualified by this probe. Neither native route may advertise strict
egress mediation from these facts. An actual native sandbox is a separate
qualification, not inferred from its name or a backend capability flag.

Optional user preference offered HTTP/JSON broker versus Codex CLI; no reply
arrived during more than a minute of independent contract analysis. Continue
with the recommended broker as the first implementation candidate, subject to
later steering. It executes no untrusted local model code: the recipient can
only request a finite structured broker protocol. It cannot supply imports,
argv, plugin/config paths, arbitrary URLs or ambient environment access. This
is a different execution boundary, not a silently weakened native route.
I01 concludes feasible to implement, NOT already qualified. I08 must prove exact
transport bytes, all request paths, OS file/ACL behavior and version binding;
fake endpoint tests do not confer control over the connected Codex host.

Current v1 contract authority:

- work_context.assignment_intent normalizes permissions and fingerprints intent;
  mutable diagnostic/provider preferences are excluded, arbitrary permission
  additions are not silently allowed.
- build_context_fields creates contract_version=1 and immutable checksums;
  validate_execution_contract rejects unsupported versions and checks pinned
  capsule bytes, current assignment intent, Work identity, source hashes and
  capability readiness. Keep v1 byte/semantic compatibility.
- execution-contract.schema.json and embedded context-capsule schema currently
  require version 1. Introduce explicit v2 and keep old-reader rejection proof;
  no security field grafted into an existing capsule.
- ProcessExecutionService.start serializes starts and resumes by objective.
  New security-aware creation/successor must reject a mismatched existing intent
  rather than returning an unrelated same-objective v1 Work. Build metadata
  before _write_capsule, never post-edit the immutable capsule. A successor
  preserves predecessor hashes and gets its own governed Work/initial stage.
- prepared_input and prepared_resources already separate private original
  material from exact source authorization. Broker calls must reauthorize and
  classify whole bounded sources before any range, with no automatic expansion
  of workspace access or model-provided classification.

Impact: new Core policy/session/storage/broker/transport modules; explicit v2
intent/schema/creation path; strict-native admission guard; CLI operator surface;
focused backward compatibility and A01-A28 tests. Existing mandatory journal,
T10 operator behavior, old prepared delivery and historical T06 original remain
protected. No actual project secrets or external model credentials are needed.

Open design work for the next stages: owner-only storage/retention, cross-process
policy+nonce linearization and crash recovery, trusted source declarations and
effect registry, exact transport envelope/response protocol, old-reader tests
and installed connected broker acceptance. I01 does not promise local isolation
or a native Codex capability. Missing/unqualified enforcement must block.
