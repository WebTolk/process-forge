"""Existing pure text rules and conflict view for project context."""

from __future__ import annotations

import re


class ProjectContextRules:
    """Evaluate existing context rules without retaining inputs or results."""

    def list_values(self, text: str, key: str) -> list[str]:
        values: list[str] = []
        lines = text.splitlines()
        key_pattern = re.compile(rf"^(\s*){re.escape(key)}\s*:\s*$")
        inline_pattern = re.compile(rf"^\s*{re.escape(key)}\s*:\s*\[(.*?)\]\s*$")
        for index, line in enumerate(lines):
            inline = inline_pattern.match(line)
            if inline:
                values.extend(item.strip().strip('"').strip("'") for item in inline.group(1).split(",") if item.strip())
                continue
            match = key_pattern.match(line)
            if not match:
                continue
            indent = len(match.group(1))
            for child in lines[index + 1 :]:
                if not child.strip():
                    continue
                child_indent = len(child) - len(child.lstrip(" "))
                if child_indent <= indent:
                    break
                stripped = child.strip()
                if stripped.startswith("- "):
                    values.append(stripped[2:].strip().strip('"').strip("'"))
        return values

    def action_rules(self, texts: dict[str, str]) -> tuple[list[str], list[str]]:
        allowed = {"read_required_sources"}
        forbidden = {"edit_forbidden_files", "rebuild_context_without_approval"}
        for text in texts.values():
            allowed.update(self.list_values(text, "allowed_actions"))
            forbidden.update(self.list_values(text, "forbidden_actions"))
        return sorted(allowed), sorted(forbidden)

    def conflict_report(self, status: str, conflicts: list[dict[str, str]], fingerprints: dict[str, str]) -> str:
        blocking = [item for item in conflicts if item["status"] == "blocked"]
        warnings = [item for item in conflicts if item["status"] == "warn"]
        approvals = [item for item in conflicts if item["status"] == "requires_approval"]
        resolved = [item for item in conflicts if item["status"] == "resolved"]

        def lines(items: list[dict[str, str]]) -> list[str]:
            return [f"- {item['message']} ({item.get('source', 'unknown')})" for item in items] or ["- None."]

        output: list[str] = [
            "schema_version: 1",
            f"status: {status}",
            f"blocking_conflicts: {len(blocking)}",
            f"warnings: {len(warnings)}",
            f"requires_approval: {len(approvals)}",
            "",
            "# Context Conflict Report",
            "",
            "## Blocking Conflicts",
            "",
            *lines(blocking),
            "",
            "## Warnings",
            "",
            *lines(warnings),
            "",
            "## Requires Approval",
            "",
            *lines(approvals),
            "",
            "## Resolved",
            "",
            *lines(resolved),
            "",
            "## Source Fingerprints",
            "",
        ]
        output.extend(f"- {path}: {fingerprint}" for path, fingerprint in fingerprints.items())
        return "\n".join(output) + "\n"
