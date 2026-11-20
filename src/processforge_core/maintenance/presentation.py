"""Text presentation of the existing update assessment."""
from __future__ import annotations

from pathlib import Path
from typing import Any


class UpdateAssessmentRenderer:
    """Render update assessment text without reading project state."""

    def render(self, project_root: Path, current_version: str, channel: str, latest: dict[str, Any] | None) -> str:
        available_version = str(latest.get("version", "none")) if latest else "none"
        migration = latest.get("migration", {}) if latest and isinstance(latest.get("migration"), dict) else {}
        changes = latest.get("changes", []) if latest and isinstance(latest.get("changes"), list) else []
        affected = latest.get("affected_files", []) if latest and isinstance(latest.get("affected_files"), list) else []

        def lines(items: list[Any], empty: str = "None.") -> str:
            if not items:
                return f"- {empty}"
            output = []
            for item in items:
                if isinstance(item, dict):
                    output.append(f"- {item.get('type', 'change')}: {item.get('summary', item)}")
                else:
                    output.append(f"- {item}")
            return "\n".join(output)

        result = "safe" if available_version in {"none", current_version} else ("requires_migration" if migration.get("required") else "requires_approval")
        return f"""# ProcessForge Update Assessment

## Status

{result}

## Project

- root: {project_root.name}
- current_version: {current_version}
- available_version: {available_version}
- channel: {channel}

## Breaking Changes

{lines([item for item in changes if isinstance(item, dict) and item.get("breaking")], "None recorded.")}

## Required Migrations

- required: {bool(migration.get("required", False))}
- guide: {migration.get("guide", "none")}

## Changes

{lines(changes)}

## Affected Files

{lines(affected, "Review `.pf/process-forge.yaml`, `.pf/hooks.yaml`, and `.pf/contexts/project-context.snapshot.*`.")}

## Required Manual Review

- Review migration guide before changing project files.
- Confirm linked distribution registry points to the intended version.
- Run public cleanliness, schema validation, checksum validation, and project doctor after migration.

## Recommended Steps

1. Read the migration guide.
2. Update the ProcessForge distribution outside the project.
3. Refresh project context.
4. Apply project migrations only with approval.
5. Re-run validation gates.

## Rollback Notes

- Keep the previous ProcessForge distribution available in the workplace registry.
- Repoint the workplace distributions registry to the previous version if migration is blocked.
- Do not delete project `.pf/` artifacts created before the update until review passes.
"""
