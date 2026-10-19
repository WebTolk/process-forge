# Restore the existing Runtime pre-bootstrap import contract

The first two existing smoke scripts passed. The third failed before entering its
main function: smoke_prepared_execution_context imports smoke_conversation_completeness,
which imports pf_runtime.host before processforge has made src available.
Host currently eagerly imports common.yaml_dump (introduced in the earlier serializer
slice) and WorkerAssignmentService (current slice). Service likewise eagerly imports
the formatter. The prior Host/Service design explicitly permits import before Core
bootstrap and uses operation-local canonical Core imports for other helpers.

This is a source bootstrap regression, not a Runtime/service infrastructure blocker.
Restore that existing import contract by moving only canonical Core dependency
imports/assembly to their actual existing call-site operations after prior guards.
Do not import Main, change paths/startup or conceal the failure in tests.

Cancel the completed initial prompts implementation Work before admitting its
successor; preserve immutable original capsule/report/proof. Three other native
contributions, all 98 Core parity comparisons and two successful scripts are retained.
Parent Main/docs/inventory file grants and capsule stay unchanged. This successor
owns the same seven product paths plus service.py solely for the observed formatter
import dependency. No lifecycle/serialization/reader behavior or external API changes.

The exact pre-correction products are frozen in bootstrap-inputs. Before-slice
consumer inputs, original prompts/proof.json/report.md and the current QA failure
are explicit additional sources. Failed/remaining scripts and an isolated import
without PYTHONPATH=src are executed by primary after correction; no successful
algorithm or unrelated script repeat. Later installed/Runtime/host qualification
and infrastructure remain outside scope.

Preserve the completed WorkerAssignmentService and all five changed smoke consumers BYTE-FOR-BYTE at the current frozen raw hashes. Preserve/reuse the original successful two-algorithm AST/signature/annotation and five synthetic proofs from prompts/proof.json; do not rerun those successful cases. Correct only eager Core imports in tools/pf_runtime/host.py and service.py. These Runtime modules intentionally import BEFORE Core bootstrap when source PYTHONPATH contains only tools; their existing canonical Core helpers such as event_journal/metrics_core import canonical modules lazily at operation time. Move the canonical dump_yaml import out of MODULE scope into the EXISTING operations/branches containing its five Host and one Service use sites. Move WorkerAssignmentService import and cold instance out of Host MODULE scope into the two EXISTING call-site operations/branches for its two load calls. Keep the actual targets, arguments, guards, JSON/YAML output paths, signatures and all other nodes/assertions unchanged. Imports should occur directly before the relevant operation/use after its prior guards, not by an eager helper bootstrap or importing Main. Canonical Core lazy import is allowed; any path back to tools/processforge.py or universal Core facade is forbidden. Do NOT add sys.path edits, import processforge or a bootstrap loader, conditional ImportError fallback, new helper functions, caches, features, permissions, startup or infrastructure. Do NOT change smoke assertions or fixtures to hide the startup failure. Service was touched by the earlier serializer slice and is explicitly owned in this successor solely to restore the same original pre-bootstrap import contract. New WorkerAssignmentService remains direct concrete Core owner. Compile only the two changed sources; at most two small AST/stub ordering checks for changed import placement; parent alone runs actual pre-bootstrap module imports and failed/unrun existing scripts. Every previous successful test and three other native contributions are retained. No model orchestration/Git/remotes/self transitions/Runtime or services. Exact SOURCE CLI selectors only if needed; never stale installed MCP. Russian report and proof.json at prompts-final: same uniform products/algorithms schema, algorithms retained from prior proof with prior_proof_sha256; consumer_preservation for all six original consumer paths with full_ast_equal/raw_only_declared_changes/substitutions (original pre-slice inputs plus explicit lazy import relocation); bootstrap_preservation for Host/Service against current bootstrap before-images, allowing ONLY relocation of the two canonical imports/Host cold instance and no other node or raw-byte delta. Prove zero eager Core imports in Host/Service and preserve original statement order. Provide exact final raw hashes for all eight owned products and mark retained cases distinctly from new cases. Read all architecture/Python/frozen sources and handoff; no successful scenario repeats.
