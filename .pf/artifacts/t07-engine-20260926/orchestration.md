# T07 engine orchestration

User explicitly added implementation of the T07 engine. This supersedes the
earlier design-only permission boundary, not its security requirements. The
installed Core update/local T10 completion is finished: 347c6d9e, official update
core-update-20260926T191610Z, 1001 installed hashes verified, live compact metrics
accepted; prior Work actually completed all nine stages and run-doctor 21 PASS.

Continue normal software-feature-development 1.1.0, one primary agent, no
subagents/workers. Current assignment/run and immutable capsule are in start.json;
capsule SHA256 000b31cf7f3af61f3b7d07943712ae201e030b7c97afb681ea85313f6792cd37.
The capsule's empty delegated-worker file scope grants no worker execution;
the primary implements the user's authorized scope documented here. No capsule
or frozen artifact rewrite. No platform/toolchain overlay selected.

Context snapshot ctx-20260925-140110-0dbc7c is fresh at creation. Connected
pf.search returned fresh index but zero authorized document coverage; pf.resolve
confirmed project.process-forge:project-artifacts at .pf/artifacts. File-first
fallback reads the original T07 spec/domain/architecture/plan/matrix. Serena
again rejected work_context.py symbols with Active languages: []; targeted UTF-8
reads/rg/AST are the documented fallback. Standard Work CLI avoids previously
reconciled MCP work-start/context 60-second post-mutation timeouts.

Sequence: intake -> I01 backend feasibility during investigation -> domain and
versioned architecture -> I02-I07 product implementation -> I08 adversarial and
compatibility assurance -> isolated archive and official Core updater delivery
-> evolve/handoff. Synthetic corpus and loopback recipients; no real project
secret transmission or external model is required. Browser/tray/remote web are
outside this task. Preserve main HEAD/dirty work, historical T06 finding and
T07 design evidence, all prior update backups and private durable fixtures.

Optional backend preference was asked: managed HTTP/JSON broker is the proposed
first route; Codex CLI is the alternative. Continue independent contract and
threat analysis while awaiting steering. A native executable does not gain a
strict capability by label or configuration. Unsupported routes fail closed.
