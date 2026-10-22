"""Advisory evidence examples from the pinned process and existing readiness results.

No file access, validation, permission grants or lifecycle decisions belong here.
"""

from __future__ import annotations

import copy
from typing import Any

from processforge_core.evidence.readiness import evidence_contract, evidence_matches

_MESSAGES = {
    "evidence_status_not_acceptable": "The latest matching record has an unacceptable status.",
    "evidence_file_unsafe": "The saved path is outside the permitted project evidence root.",
    "evidence_file_missing": "The saved evidence file no longer exists.",
    "evidence_file_not_regular": "The saved path is not a regular file.",
    "evidence_file_unreadable": "PF cannot read the saved evidence file.",
    "evidence_digest_missing": "The saved file record has no digest; resubmit the actual file.",
    "evidence_file_changed": "The file differs from its saved digest; review and resubmit it.",
    "invalid_evidence": "An evidence entry must be an object or an attestation string.",
    "not_applicable_evidence_incomplete": "not_applicable requires a nonempty reason and a nonempty evidence list.",
    "artifact_path_missing": "A supplied path must resolve to an existing regular file inside the authorized project root.",
    "artifact_path_unreadable": "PF could not read or hash the supplied file.",
    "outcome_not_allowed": "Choose an outcome offered by the current pinned stage.",
}


def _objects(value: Any) -> list[dict[str, Any]]:
    return (
        [item for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def _example(kind: str, identifier: str) -> dict[str, Any]:
    contract = evidence_contract(kind)
    return {
        "kind": contract["kinds"][0],
        contract["id_keys"][0]: identifier,
        "status": "approved" if kind == "gate" else "ready",
    }


class EvidenceGuidancePolicy:
    def _requirements(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for field, kind in (
            ("required_inputs", "input"),
            ("artifacts", "artifact"),
            ("required_evidence", "evidence"),
        ):
            refs.extend(
                {**item, "requirement_kind": kind}
                for item in _objects(state.get(field))
            )
        gates = state.get("gates") or {}
        for phase in ("entry", "exit"):
            refs.extend(
                {**item, "requirement_kind": "gate", "phase": phase}
                for item in _objects(gates.get(phase))
            )
        return refs

    def _next_entries(
        self, state: dict[str, Any], process: dict[str, Any]
    ) -> list[dict[str, Any]]:
        stages = {
            str(item["id"]): item
            for item in _objects(process.get("stages"))
            if item.get("id") and item.get("executable", True) is not False
        }
        definitions = {
            str(item.get("id")): item for item in _objects(process.get("gates"))
        }
        result = []
        for outcome in _objects(state.get("allowed_outcomes")):
            target = str(outcome.get("next_stage") or "")
            gates = stages.get(target, {}).get("entry_gates")
            for gate_id in gates if isinstance(gates, list) else []:
                identifier = str(gate_id)
                definition = definitions.get(identifier, {})
                result.append(
                    {
                        "id": identifier,
                        "requirement_kind": "gate",
                        "phase": "next_entry",
                        "for_outcome": str(outcome.get("id") or ""),
                        "target_stage": target,
                        "evaluation": "conditional_not_evaluated",
                        # Transition entry checks use blocking alone, unlike
                        # current-stage readiness's required-and-blocking rule.
                        "required_for_transition": bool(
                            definition.get("blocking", True)
                        ),
                        "accepted": evidence_contract("gate"),
                        "example": _example("gate", identifier),
                    }
                )
        return result

    def _unmatched(
        self, evidence: list[dict[str, Any]], refs: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        observations = []
        id_keys = ("input_id", "artifact_id", "evidence_id", "gate_id", "id")
        for index, item in enumerate(evidence):
            if any(
                evidence_matches(ref["requirement_kind"], str(ref["id"]), item)
                for ref in refs
            ):
                continue
            identifiers = {str(item.get(key) or "") for key in id_keys} - {""}
            same_id = [ref for ref in refs if str(ref["id"]) in identifiers]
            if not identifiers:
                code = "identifier_missing"
            elif same_id:
                code = (
                    "identifier_field_mismatch"
                    if any(
                        str(item.get("kind") or "")
                        in evidence_contract(ref["requirement_kind"])["kinds"]
                        for ref in same_id
                    )
                    else "kind_mismatch"
                )
            else:
                code = "identifier_not_expected"
            observations.append(
                {
                    "index": index,
                    "code": code,
                    "message": "This saved record does not match a declared current requirement or conditional next-entry gate. Supplemental evidence may still be retained; this observation is not a rejection.",
                }
            )
        return observations

    def project(
        self, state: dict[str, Any], *, process: dict[str, Any]
    ) -> dict[str, Any]:
        guidance: dict[str, Any] = {
            "schema_version": 1,
            "stage_id": str((state.get("stage") or {}).get("id") or ""),
            "advisory": True,
            "applicable": False,
        }
        if (
            state.get("action") not in {"work_ready", "work_incomplete"}
            or (state.get("assignment") or {}).get("status")
            in {"done", "completed", "cancelled", "failed"}
            or (state.get("run") or {}).get("status")
            in {"completed", "cancelled", "failed"}
            or (state.get("execution_readiness") or {}).get("status") != "ready"
            or ((state.get("context") or {}).get("validation") or {}).get("status")
            != "valid"
            or (state.get("process") or {}).get("pin_status") != "pinned"
        ):
            guidance["reason"] = (
                "Work must be active with valid pinned context and ready permissions. Follow its existing blockers."
            )
            return guidance

        refs = self._requirements(state)
        missing = []
        for ref in refs:
            if ref.get("satisfied"):
                continue
            kind, identifier = ref["requirement_kind"], str(ref["id"])
            example = _example(kind, identifier)
            item = {
                "id": identifier,
                "requirement_kind": kind,
                "required_for_transition": kind != "gate"
                or bool(ref.get("required", True))
                and bool(ref.get("blocking", True)),
                "accepted": evidence_contract(kind),
                "example": example,
                "not_applicable_example": {
                    **example,
                    "status": "not_applicable",
                    "reason": "<actual justification>",
                    "evidence": ["<supporting evidence>"],
                },
            }
            if "phase" in ref:
                item["phase"] = ref["phase"]
            diagnostic = ref.get("diagnostic")
            if isinstance(diagnostic, dict):
                code = str(diagnostic.get("code") or "")
                item["mismatch"] = {
                    "code": code,
                    "message": _MESSAGES.get(
                        code, "Follow the existing requirement diagnostic."
                    ),
                }
            else:
                item["mismatch"] = {
                    "code": "matching_record_missing",
                    "message": "No matching record is available in this requirement's evidence scope.",
                }
            missing.append(item)

        next_entries = self._next_entries(state, process)
        codes = {item.get("code") for item in _objects(state.get("incomplete"))}
        submission = [
            copy.deepcopy(item["example"])
            for item in missing
            if item["required_for_transition"]
        ]
        if "stage_evidence_required" in codes and not submission:
            submission.append(
                {
                    "kind": "attestation",
                    "id": "<supporting evidence id>",
                    "status": "ready",
                    "summary": "<actual completed work>",
                }
            )
        outcomes = [
            str(item.get("id") or "")
            for item in _objects(state.get("allowed_outcomes"))
        ]
        template: dict[str, Any] = {
            "project_root": "<project root>",
            "run_id": (state.get("run") or {}).get("id"),
            "assignment_id": (state.get("assignment") or {}).get("id"),
            "context_id": (state.get("context") or {}).get("id"),
            "outcome": outcomes[0]
            if len(outcomes) == 1
            else "<one of allowed_outcomes>",
            "evidence": submission,
        }
        if "handoff_note_required" in codes:
            template["notes"] = (
                "<handoff describing completed work and remaining limits>"
            )
        guidance.update(
            {
                "applicable": True,
                "requirements": missing,
                "conditional_next_entry_gates": next_entries,
                "unmatched_evidence": self._unmatched(
                    _objects(state.get("evidence")), refs + next_entries
                ),
                "transition_template": template,
                "optional_file_fields": {
                    "path": "<existing authorized project-relative file>"
                },
                "usage": [
                    "Replace placeholders with truthful evidence after completing the work; examples grant no permissions.",
                    "A path is optional. When supplied, PF hashes the actual file; saved-file freshness checks remain authoritative.",
                    "Requirements use the latest matching record. Inputs/entry gates may use accumulated evidence; outputs/exit gates use current-stage evidence.",
                    "For gates, a nonempty gate_id takes precedence over id; other requirement ID aliases are alternatives.",
                    "Conditional next-entry gates depend on the chosen outcome and may already be satisfied by accumulated evidence. They are not evaluated here.",
                    "not_applicable needs an actual reason and supporting evidence; notes belong in transition.notes.",
                ],
            }
        )
        return guidance

    def request_errors(self, blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "code": item["code"],
                **({"index": item["index"]} if "index" in item else {}),
                "message": _MESSAGES[item["code"]],
            }
            for item in blockers
            if item.get("code") in _MESSAGES
        ]
