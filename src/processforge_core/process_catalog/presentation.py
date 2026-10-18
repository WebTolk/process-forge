from __future__ import annotations

from typing import Any

from processforge_core.common.checks import Check
from processforge_core.common.ids import title_from_id
from processforge_core.common.values import as_list
from processforge_core.process_catalog.coordination import process_coordination_requirements


class ProcessAuthoringRenderer:
    def questions(self, answers: dict[str, Any]) -> str:
        process = answers.get("process") if isinstance(answers.get("process"), dict) else {}
        return "\n".join(
            [
                f"# Process Authoring Questions: {process.get('name', process.get('id', 'process'))}",
                "",
                "- What concrete outcome must this process produce?",
                "- Which roles own each stage and artifact?",
                "- Which artifacts prove that a stage is complete?",
                "- Which blocking gates can stop apply or completion?",
                "- Does the process need multiple assignment-backed tasks or one linear flow?",
                "- Which execution mode applies: single_agent, single_agent_with_subagents, orchestrated_agents, or process_factory?",
                "- For single_agent mode, which CLI checks and gates replace separate Inspector/Supervisor work?",
                "- Can this process run in simple project mode?",
                "- Does this process require organized project mode or only optionally use Director when available?",
                "- Should worker agents submit reports to Director inbox?",
                "- Should errors go to Director inbox, a process route, or the operator?",
                "- If the project is simple, should Director-related features be disabled, optional, or fail validation?",
                "- Is common process evolve enabled or disabled for this process?",
                "- If evolve is disabled, what reason should be recorded in `evolve.reason`?",
                "- If evolve is enabled, which mode, timing, default scope, candidate targets, candidate targeting, extraction hints, privacy boundary, apply policy, and required outputs apply?",
                "- Which target layer should receive each knowledge candidate?",
                "- Where does each candidate apply, where does it not apply, and which source context proves that boundary?",
                "- Should a mixed observation be split into multiple candidates before any generalization or promotion?",
                "- What reusable knowledge may appear during this process?",
                "- Which outputs are candidates for shared packages, and what must remain project-private?",
                "- Which examples should prove the generated process is usable?",
                "",
                "Answers are stored in `answers.yaml`; the generated candidate is `draft.process.yaml`.",
            ]
        ) + "\n"

    def logic_review(self, process: dict[str, Any], checks: list[Check]) -> str:
        lines = [f"# Process Logic Review: {process.get('id', 'process')}", "", "| Level | Check |", "| --- | --- |"]
        for item in checks:
            lines.append(f"| {item.level} | {item.message} |")
        failures = [item for item in checks if item.level == "FAIL"]
        warnings = [item for item in checks if item.level == "WARN"]
        lines.extend(["", f"Result: `{'fail' if failures else 'pass'}`", f"Failures: `{len(failures)}`", f"Warnings: `{len(warnings)}`", ""])
        return "\n".join(lines)

    def agent_prompt(self, process: dict[str, Any]) -> str:
        process_id = str(process.get("id", "process"))
        coordination = process_coordination_requirements(process)
        lines = [
            f"# {process.get('name', title_from_id(process_id))} Agent",
            "",
            f"Process id: `{process_id}`",
            "",
            "Use the governed high-level workflow:",
            "",
            "```bash",
            "pf.context",
            "pf.work.start(objective)",
            "pf.work.state()",
            "pf.work.transition(outcome, evidence, notes)",
            "# Repeat state/transition until action=run_completed.",
            "```",
            "",
            "Rules:",
            "",
            "- Treat pf.work.state as the source of truth for the current stage and allowed outcomes.",
            f"- Execution mode: `{process.get('execution_mode', 'single_agent')}`.",
            f"- Coordination requirement: `{coordination.get('mode', 'simple_allowed')}`.",
            "- Record durable artifacts for every blocking gate.",
            "- Run review before handoff when the process defines a review stage.",
            "- Keep public files portable and free of secrets.",
            "- Do not choose the next stage or create Run/Assignment records manually during normal work.",
        ]
        return "\n".join(lines) + "\n"

    def document(self, process: dict[str, Any]) -> str:
        process_id = str(process.get("id", "process"))
        coordination = process_coordination_requirements(process)
        error_handling = process.get("error_handling") if isinstance(process.get("error_handling"), dict) else {}
        lines = [
            f"# {process.get('name', title_from_id(process_id))}",
            "",
            str(process.get("description", "")),
            "",
            f"- process_id: `{process_id}`",
            f"- version: `{process.get('version', '')}`",
            f"- status: `{process.get('status', '')}`",
            f"- scope: `{process.get('scope', 'project')}`",
            f"- execution_mode: `{process.get('execution_mode', 'single_agent')}`",
            f"- coordination_requirement: `{coordination.get('mode', 'simple_allowed')}`",
            f"- error_handling: `{error_handling.get('mode', coordination.get('error_workflow', {}).get('mode', 'none'))}`",
            "",
            "## Stages",
            "",
        ]
        for stage in as_list(process.get("stages")):
            if isinstance(stage, dict):
                lines.append(f"- `{stage.get('id')}`: {stage.get('description') or stage.get('title', '')}")
        lines.extend(["", "## Artifacts", ""])
        for artifact in as_list(process.get("artifact_definitions")):
            if isinstance(artifact, dict):
                lines.append(f"- `{artifact.get('id')}`: {artifact.get('title', '')}")
        lines.extend(["", "## Gates", ""])
        for gate_item in as_list(process.get("gates")):
            if isinstance(gate_item, dict):
                lines.append(f"- `{gate_item.get('id')}`: {gate_item.get('description', '')}")
        return "\n".join(lines) + "\n"
