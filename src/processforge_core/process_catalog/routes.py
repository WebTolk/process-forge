"""Read process routes and preserve their existing semantic checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.checks import Check, check
from ..common.ids import safe_id
from ..maintenance.schema_checks import UpdateSchemaChecks
from .contracts import HANDOFF_MODES, ProcessRouteDocumentReader


class ProcessRouteService:
    """Own route lookup and validation using current document reads."""

    def __init__(self, distribution_root: Path) -> None:
        self.routes = ProcessRouteDocumentReader()
        self.schema_checks = UpdateSchemaChecks(distribution_root)

    def by_id(self, project_root: Path, route_id: str) -> dict[str, Any]:
        route_id = safe_id(route_id, "route")
        routes = self.routes.read(project_root).get("routes", [])
        for route in routes if isinstance(routes, list) else []:
            if isinstance(route, dict) and str(route.get("id")) == route_id:
                return route
        raise SystemExit(f"FAIL: process route not found: {route_id}")

    def validate(self, project_root: Path) -> list[Check]:
        data = self.routes.read(project_root)
        routes = data.get("routes") if isinstance(data.get("routes"), list) else []
        checks = [check("PASS" if data.get("schema_version") else "FAIL", "process route map schema_version present")]
        self.schema_checks.append(checks, data, "process-route-map.schema.json", "process route map")
        seen: set[str] = set()
        for route in routes:
            if not isinstance(route, dict):
                checks.append(check("FAIL", "route item must be object"))
                continue
            route_id = safe_id(str(route.get("id") or ""), "route")
            checks.append(check("PASS" if route_id and route_id not in seen else "FAIL", f"route id unique: {route_id or 'missing'}"))
            seen.add(route_id)
            checks.append(check("PASS" if route.get("from_process") else "FAIL", f"{route_id} from_process present"))
            checks.append(check("PASS" if route.get("to_process") else "FAIL", f"{route_id} to_process present"))
            checks.append(check("PASS" if str(route.get("mode") or "") in HANDOFF_MODES else "FAIL", f"{route_id} mode valid"))
        return checks

    def required_role(self, route: dict[str, Any]) -> str:
        requires = route.get("requires_agent") if isinstance(route.get("requires_agent"), dict) else {}
        return str(requires.get("role") or "")
