from __future__ import annotations

from pathlib import Path
from typing import Any

from processforge_core.common.ids import title_from_id
from processforge_core.common.text import ensure_trailing_newline
from processforge_core.common.yaml_dump import dump_yaml


def process_yaml_content(value: dict[str, Any]) -> bytes:
    return ensure_trailing_newline(dump_yaml(value)).encode("utf-8")


class ProcessAuthoringExampleBuilder:
    def build(
        self,
        project_root: Path,
        process: dict[str, Any],
        answers: dict[str, Any],
        review_text: str,
    ) -> list[tuple[Path, bytes]]:
        process_id = str(process.get("id") or "process")
        example_root = project_root / "examples" / "process-authoring" / process_id
        title = str(process.get("name") or title_from_id(process_id))
        readme = "\n".join(
            [
                f"# Process Authoring Example: {title}",
                "",
                "This example shows the authoring inputs, generated process draft, and logic review produced before apply.",
                "",
                "```bash",
                f"python bin/pf.py process-create --project-root <project-root> --answers examples/process-authoring/{process_id}/answers.yaml --apply",
                f"python bin/pf.py process-doctor --project-root <project-root> --process {process_id}",
                "```",
                "",
            ]
        )
        return [
            (example_root / "README.md", readme.encode("utf-8")),
            (example_root / "answers.yaml", process_yaml_content(answers)),
            (example_root / "draft.process.yaml", process_yaml_content(process)),
            (example_root / "logic-review.md", review_text.encode("utf-8")),
            (
                example_root / f"process-authoring-{process_id}-report.md",
                f"# {title} Process Authoring Report\n\nStatus: authored and applied through ProcessForge process authoring.\n".encode("utf-8"),
            ),
            (
                example_root / f"process-authoring-{process_id}-review.md",
                f"# {title} Process Authoring Review\n\nResult: pass.\n".encode("utf-8"),
            ),
            (
                example_root / f"process-authoring-{process_id}-handoff.md",
                f"# {title} Process Authoring Handoff\n\nThe example process is ready for `process-doctor` and task-batch use.\n".encode("utf-8"),
            ),
        ]
