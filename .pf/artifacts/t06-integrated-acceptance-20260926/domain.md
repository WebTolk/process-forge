# T06 domain rules

Status: ready_for_review. No new domain model is introduced.

Work is the durable Run/Assignment plus immutable context identity. Executor preference and transport session are replaceable; intent, source pins and permission grants are not. Governed worker collection records execution output without moving the primary process stage or completing its assignment. Only a valid declared outcome/evidence transition advances the pinned process. Legacy task collection retains its compatibility completion events, exactly once across interruption.

A prepared attempt is an immutable private input and attributable result boundary. A receipt pins output bytes; a completion record closes publication. A collector dying after receipt/events but before completion may leave a dead-owner lifecycle lock; a later collector must recover it and avoid duplicate events. Private paths must reject real directory redirection, including Windows Junctions, even if the target stays inside the project.

Evidence classes: declarations describe intended permissions/capabilities; deterministic tests prove bounded observed behavior; semantic review judges whether tests and docs match the contract. None implies OS confinement. Source, isolated source MCP/Runtime, installed subprocess MCP, and actual connected-host MCP are separate evidence layers. Optional diagnostics profiles may change diagnostics only, never mandatory process evidence or stdout framing.
