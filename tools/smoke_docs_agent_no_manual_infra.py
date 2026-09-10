#!/usr/bin/env python3
"""Guard Garage-first agent instructions against manual infrastructure work."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    files = [
        ROOT / "templates" / "project-agents-template.md",
        ROOT / "templates" / "global-agents-processforge-section.md",
        ROOT / ".pf" / "AGENTS.md",
        ROOT / "tools" / "processforge.py",
        ROOT / "prompts" / "task-batch-execution-agent.md",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        for marker in ["pf.context", "pf.search", "pf.resolve", "pf.work.start"]:
            if marker not in text:
                raise AssertionError(f"{path.relative_to(ROOT)} missing {marker}")
        if not re.search(r"do not (?:install|start|restart|repair)", text.lower()):
            raise AssertionError(f"{path.relative_to(ROOT)} lacks the infrastructure boundary")
    task_batch = (ROOT / "prompts" / "task-batch-execution-agent.md").read_text(encoding="utf-8")
    for marker in [
        "compatibility task-batch example",
        "not a fallback",
        "operator diagnostic",
        "pf.work.state",
        "pf.work.transition",
        "process_choice_required",
        "run_completed",
    ]:
        if marker not in task_batch:
            raise AssertionError(f"prompts/task-batch-execution-agent.md missing: {marker}")
    manual_command = re.compile(r"(?im)^\s*(?:python|python3|pwsh|powershell|docker|systemctl|pip)\b.*(?:mcp|ledger|runtime|hook|install|restart|repair)")
    if manual_command.search(task_batch):
        raise AssertionError("specialized task-batch prompt contains an executable manual infrastructure command")
    print("PASS: agent instructions use the high-level Garage path and prohibit manual infrastructure repair")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
