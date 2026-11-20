"""The existing workspace resource-reference matching policy."""

from __future__ import annotations

from typing import Any


class WorkspaceAccessReferenceService:
    """Match declared references without resolving paths or authorizing access."""

    def workspace_ref_matches_resource(self, resource: dict[str, Any], requested: Any) -> bool:
        if isinstance(requested, dict):
            if requested.get("path_ref") and resource.get("path_ref") == requested.get("path_ref"):
                return True
            requested_id = str(requested.get("id") or requested.get("resource_id") or "").strip()
            requested_package = str(requested.get("package_id") or requested.get("package") or "").strip()
        else:
            text = str(requested).strip()
            if text == "*":
                return True
            requested_package, _, requested_id = text.partition(":")
            if not requested_id:
                requested_id = requested_package
                requested_package = ""
        ids = {
            str(resource.get("id") or ""),
            str(resource.get("instance_id") or ""),
        }
        for value in list(ids):
            if ":" in value:
                ids.add(value.rsplit(":", 1)[-1])
            if "@" in value:
                ids.add(value.split("@", 1)[0])
        package_id = str(resource.get("package_id") or "")
        ids.add(f"{package_id}:{resource.get('id')}")
        ids.add(f"{package_id}:{resource.get('instance_id')}")
        if requested_id not in ids:
            return False
        return not requested_package or requested_package == package_id
