"""Markdown presentation for process import and parity."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from processforge_core.common.checks import Check
from processforge_core.common.paths import rel
from processforge_core.common.status import aggregate_status


class ProcessParityRenderer:

    def import_report(self, process: dict[str, Any], process_path: Path, paths: dict[str, Path], project_root: Path, unsupported: list[dict[str, str]]) -> str:
        status = "WARN" if unsupported else "PASS"
        lines = [
            f"# Process Authoring Import: {process.get('id', process_path.stem)}",
            "",
            "## Result",
            "",
            status,
            "",
            "## Source",
            "",
            f"- Path: `{rel(process_path, project_root)}`",
            f"- Process id: `{process.get('id', process_path.stem)}`",
            "",
            "## Created",
            "",
            f"- `{rel(paths['answers'], project_root)}`",
            f"- `{rel(paths['draft'], project_root)}`",
            f"- `{rel(paths['source'], project_root)}`",
            f"- `{rel(paths['semantic_map'], project_root)}`",
            f"- `{rel(paths['unsupported'], project_root)}`",
            "",
            "## Unsupported Fields",
            "",
        ]
        if unsupported:
            lines.extend(f"- `{item['path']}`: {item['reason']}" for item in unsupported)
        else:
            lines.append("- None.")
        return "\n".join(lines) + "\n"

    def parity_report(self, process_id: str, source_path: Path, project_root: Path, status: str, diffs: list[dict[str, str]], unsupported: list[dict[str, str]], logic_checks: list[Check]) -> str:
        lines = [
            f"# Process Parity: {process_id}",
            "",
            "## Result",
            "",
            status,
            "",
            "## Source",
            "",
            f"- Path: `{rel(source_path, project_root)}`",
            f"- Process id: `{process_id}`",
            "",
            "## Authoring Coverage",
            "",
            "| Area | Status | Notes |",
            "|---|---|---|",
        ]
        logic_diff_levels = [item["level"] for item in diffs if item["area"] == "logic_review"]
        logic_status = "FAIL" if "FAIL" in logic_diff_levels else ("WARN" if "WARN" in logic_diff_levels else "PASS")
        lines.append(f"| logic_review | {logic_status} | {len(logic_checks)} checks |")
        lines.append(f"| unsupported_fields | {'WARN' if unsupported else 'PASS'} | {len(unsupported)} unsupported fields |")
        lines.append(f"| semantic_diff | {status} | {len(diffs)} differences |")
        lines.extend(["", "## Semantic Diff", ""])
        if diffs:
            lines.extend(f"- {item['level']} `{item['area']}`: {item['message']}" for item in diffs)
        else:
            lines.append("- No meaningful differences.")
        lines.extend(["", "## Unsupported Fields", ""])
        if unsupported:
            lines.extend(f"- `{item['path']}`: {item['reason']}" for item in unsupported)
        else:
            lines.append("- None.")
        expected_warns = [item for item in diffs if item["level"] == "WARN" and item["area"] in {"logic_review", "unsupported_fields"}]
        action_warns = [item for item in diffs if item["level"] == "WARN" and item["area"] not in {"logic_review", "unsupported_fields"}]
        lines.extend(["", "## Checked", ""])
        lines.append("- Process id, run model, roles, stages, artifacts, gates, emitted events, and resource requirements.")
        lines.append("- Candidate process logic against ProcessForge authoring rules.")
        lines.extend(["", "## Skipped", ""])
        lines.append("- Byte-for-byte YAML formatting and key order are intentionally not compared.")
        lines.extend(["", "## Expected WARN", ""])
        if expected_warns:
            lines.extend(f"- `{item['area']}`: {item['message']}" for item in expected_warns)
        else:
            lines.append("- None.")
        lines.extend(["", "## Public Release WARN Actions", ""])
        if action_warns:
            lines.extend(f"- `{item['area']}`: {item['message']}" for item in action_warns)
        else:
            lines.append("- None.")
        lines.extend(["", "## Recommendation", ""])
        if status == "PASS":
            lines.append("Process is semantically reproducible through authoring import.")
        elif status == "WARN":
            lines.append("Process is reproducible with documented warnings; public-release action items are listed explicitly when present.")
        else:
            lines.append("Process is not reproducible enough for release parity; fix FAIL items before public release.")
        return "\n".join(lines) + "\n"

    def index(self, rows: list[dict[str, Any]], title: str) -> str:
        result = aggregate_status([str(item.get("result", "")) for item in rows])
        counts = {status: sum(1 for item in rows if item.get("result") == status) for status in ["PASS", "WARN", "SKIP", "FAIL"]}
        lines = [
            f"# {title}",
            "",
            f"Result: `{result}`",
            "",
            "## Summary",
            "",
            f"- PASS: {counts['PASS']}",
            f"- WARN: {counts['WARN']}",
            f"- SKIP: {counts['SKIP']}",
            f"- FAIL: {counts['FAIL']}",
            "",
            "## Checked",
            "",
            "- Semantic parity for process definitions discovered by ProcessForge.",
            "- Generated authoring backfill candidates and semantic diff artifacts.",
            "",
            "## Skipped",
            "",
            "- Byte-for-byte YAML formatting and key order are intentionally not compared.",
            "",
            "## Items",
            "",
            "| Item | Result | Source | Review |",
            "|---|---|---|---|",
        ]
        for item in rows:
            name = str(item.get("process_id") or item.get("id") or "item")
            lines.append(f"| `{name}` | {item.get('result', '')} | `{item.get('source', '')}` | `{item.get('review', '')}` |")
        return "\n".join(lines) + "\n"
