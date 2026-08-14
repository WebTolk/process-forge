# Package Bootstrap Patch

```diff
diff --git a/src/processforge_core/__init__.py b/src/processforge_core/__init__.py
new file mode 100644
--- /dev/null
+++ b/src/processforge_core/__init__.py
@@ -0,0 +1,5 @@
+"""Package bootstrap seam for direct-script ProcessForge runtime adapters."""
+
+from .bootstrap import RuntimeBootstrap, bootstrap_runtime
+
+__all__ = ["RuntimeBootstrap", "bootstrap_runtime"]
diff --git a/src/processforge_core/bootstrap.py b/src/processforge_core/bootstrap.py
new file mode 100644
--- /dev/null
+++ b/src/processforge_core/bootstrap.py
@@ -0,0 +1,77 @@
+"""Bootstrap direct-script runtime adapters onto the packaged ProcessForge core."""
+
+from __future__ import annotations
+
+import importlib
+import importlib.util
+import sys
+from dataclasses import dataclass
+from pathlib import Path
+from types import ModuleType
+
+LEGACY_CORE_MODULE_NAME = "processforge_core._legacy_processforge"
+LEGACY_PUBLIC_MODULE_NAME = "processforge"
+
+
+@dataclass(frozen=True)
+class RuntimeBootstrap:
+    repo_root: Path
+    core: ModuleType
+    host: ModuleType
+    service: ModuleType
+
+
+def _repo_root_from(caller_file: str | Path) -> Path:
+    caller_path = Path(caller_file).resolve()
+    for candidate in (caller_path.parent, *caller_path.parents):
+        if (candidate / "tools" / "processforge.py").is_file():
+            return candidate
+    raise RuntimeError(f"could not resolve repository root from {caller_path}")
+
+
+def _ensure_sys_path(path: Path) -> None:
+    value = str(path)
+    if value not in sys.path:
+        sys.path.insert(0, value)
+
+
+def _cached_legacy_core(script_path: Path) -> ModuleType | None:
+    for name in (LEGACY_CORE_MODULE_NAME, LEGACY_PUBLIC_MODULE_NAME):
+        module = sys.modules.get(name)
+        if isinstance(module, ModuleType) and Path(getattr(module, "__file__", "")).resolve() == script_path:
+            sys.modules[LEGACY_CORE_MODULE_NAME] = module
+            sys.modules[LEGACY_PUBLIC_MODULE_NAME] = module
+            return module
+    return None
+
+
+def _load_legacy_core(repo_root: Path) -> ModuleType:
+    script_path = (repo_root / "tools" / "processforge.py").resolve()
+    cached = _cached_legacy_core(script_path)
+    if cached is not None:
+        return cached
+    spec = importlib.util.spec_from_file_location(LEGACY_CORE_MODULE_NAME, script_path)
+    if spec is None or spec.loader is None:
+        raise ImportError(f"could not load legacy core module: {script_path}")
+    module = importlib.util.module_from_spec(spec)
+    sys.modules[LEGACY_CORE_MODULE_NAME] = module
+    sys.modules[LEGACY_PUBLIC_MODULE_NAME] = module
+    try:
+        spec.loader.exec_module(module)
+    except Exception:
+        if sys.modules.get(LEGACY_CORE_MODULE_NAME) is module:
+            sys.modules.pop(LEGACY_CORE_MODULE_NAME, None)
+        if sys.modules.get(LEGACY_PUBLIC_MODULE_NAME) is module:
+            sys.modules.pop(LEGACY_PUBLIC_MODULE_NAME, None)
+        raise
+    return module
+
+
+def bootstrap_runtime(caller_file: str | Path) -> RuntimeBootstrap:
+    repo_root = _repo_root_from(caller_file)
+    _ensure_sys_path(repo_root / "src")
+    _ensure_sys_path(repo_root / "tools")
+    core = _load_legacy_core(repo_root)
+    host = importlib.import_module("pf_runtime.host")
+    service = importlib.import_module("pf_runtime.service")
+    return RuntimeBootstrap(
+        repo_root=repo_root,
+        core=core,
+        host=host,
+        service=service,
+    )
diff --git a/tools/pf_runtime/mcp_server.py b/tools/pf_runtime/mcp_server.py
--- a/tools/pf_runtime/mcp_server.py
+++ b/tools/pf_runtime/mcp_server.py
@@ -1,79 +1,108 @@
 """Small read-only stdio MCP facade over existing PF Runtime/Core readers."""

 from __future__ import annotations

 import argparse
-import importlib
+import importlib.util
 import json
 import os
 import sys
 from pathlib import Path
 from typing import Any

-TOOLS_ROOT = str(Path(__file__).resolve().parents[1])
-if TOOLS_ROOT not in sys.path:
-    sys.path.insert(0, TOOLS_ROOT)
-
+_RUNTIME_BOOTSTRAP: Any | None = None

 TOOLS = {
     "pf.project_state": "Read the current routed ProcessForge project state.",
     "pf.work_state": "Read current ProcessForge work state.",
     "pf.resolve": "Resolve a ProcessForge project or selected knowledge resource.",
     "pf.workplace_state": "Read derived workplace ledger state.",
 }


-def core_module() -> Any:
-    return importlib.import_module("processforge")
+def runtime_bootstrap() -> Any:
+    global _RUNTIME_BOOTSTRAP
+    if _RUNTIME_BOOTSTRAP is None:
+        repo_root = Path(__file__).resolve().parents[2]
+        module_name = "processforge_core.bootstrap"
+        module = sys.modules.get(module_name)
+        if module is None:
+            bootstrap_path = repo_root / "src" / "processforge_core" / "bootstrap.py"
+            spec = importlib.util.spec_from_file_location(module_name, bootstrap_path)
+            if spec is None or spec.loader is None:
+                raise ImportError(f"could not load bootstrap module: {bootstrap_path}")
+            module = importlib.util.module_from_spec(spec)
+            sys.modules[module_name] = module
+            spec.loader.exec_module(module)
+        _RUNTIME_BOOTSTRAP = module.bootstrap_runtime(__file__)
+    return _RUNTIME_BOOTSTRAP


-def tool_result(name: str, arguments: dict[str, Any], workplace: Path, session_id: str, core: Any) -> dict[str, Any]:
-    from pf_runtime import host
-
+def tool_result(name: str, arguments: dict[str, Any], workplace: Path, session_id: str, runtime: Any) -> dict[str, Any]:
+    host = runtime.host
+    core = runtime.core
     supplied_session = str(arguments.get("session_id") or session_id or "")
     if not supplied_session:
         raise ValueError("PF_MCP_SESSION_ID or session_id is required")
     project_root = arguments.get("project_root")
     # A stdio MCP server has no HTTP handler to enforce this for us.  Bind the
     # supplied session to Ledger first and reject every conflicting project.
     bound_project = host.project_for_session(argparse.Namespace(session=supplied_session, project_root=None), workplace, core)
     if project_root:
         requested_project = host.resolve_project(str(project_root), core)
         if core.project_id(bound_project) != core.project_id(requested_project):
             raise PermissionError("session is not authorized for requested project_root")
     if name == "pf.project_state":
         return host.project_state_payload(workplace, core, session=supplied_session)
     if name == "pf.work_state":
         return host.work_state_payload(workplace, core, session=supplied_session)
     if name == "pf.resolve":
         return host.resolve_payload(workplace, core, session=supplied_session, resource_id=str(arguments.get("resource_id") or "") or None)
     if name == "pf.workplace_state":
         return host.workplace_state_payload(workplace, core)
     raise ValueError(f"unknown tool: {name}")


-def respond(request: dict[str, Any], workplace: Path, session_id: str, core: Any) -> dict[str, Any] | None:
+def respond(request: dict[str, Any], workplace: Path, session_id: str, runtime: Any) -> dict[str, Any] | None:
+    core = runtime.core
     method = str(request.get("method") or "")
     request_id = request.get("id")
     if method == "notifications/initialized":
         return None
     if method == "initialize":
         return {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "processforge", "version": str(getattr(core, "PROCESSFORGE_VERSION", "1"))}, "capabilities": {"tools": {}}}}
     if method == "tools/list":
         tools = [{"name": name, "description": description, "inputSchema": {"type": "object", "properties": {"session_id": {"type": "string"}, "project_root": {"type": "string"}, "resource_id": {"type": "string"}}}} for name, description in TOOLS.items()]
         return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
     if method == "tools/call":
         params = request.get("params") if isinstance(request.get("params"), dict) else {}
         try:
-            result = tool_result(str(params.get("name") or ""), params.get("arguments") if isinstance(params.get("arguments"), dict) else {}, workplace, session_id, core)
+            result = tool_result(str(params.get("name") or ""), params.get("arguments") if isinstance(params.get("arguments"), dict) else {}, workplace, session_id, runtime)
             return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, sort_keys=True)}]}}
         except Exception as exc:
             return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": str(exc)}], "isError": True}}
     return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "method not found"}}


 def main() -> int:
     parser = argparse.ArgumentParser()
     parser.add_argument("--workplace", required=True)
     parser.add_argument("--session", default=os.environ.get("PF_MCP_SESSION_ID", ""))
     args = parser.parse_args()
-    core = core_module()
+    runtime = runtime_bootstrap()
+    core = runtime.core
     workplace = core.resolve_workplace_root(args.workplace)
     for line in sys.stdin:
         if not line.strip():
             continue
         try:
-            response = respond(json.loads(line), workplace, args.session, core)
+            response = respond(json.loads(line), workplace, args.session, runtime)
             if response is not None:
                 print(json.dumps(response, ensure_ascii=False), flush=True)
         except Exception as exc:
             print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}, ensure_ascii=False), flush=True)
     return 0
diff --git a/tools/pf_runtime/codex_hooks.py b/tools/pf_runtime/codex_hooks.py
--- a/tools/pf_runtime/codex_hooks.py
+++ b/tools/pf_runtime/codex_hooks.py
@@ -1,95 +1,126 @@
 """Thin Codex lifecycle-hook adapter for the local PF Runtime.

 It converts documented hook facts into normalized events and deliberately
 returns success when the current directory is not a ProcessForge project.
 """

 from __future__ import annotations

 import argparse
 import contextlib
-import importlib
+import importlib.util
 import io
 import json
 import os
 import sys
 from pathlib import Path
 from typing import Any

-TOOLS_ROOT = str(Path(__file__).resolve().parents[1])
-if TOOLS_ROOT not in sys.path:
-    sys.path.insert(0, TOOLS_ROOT)
-
+_RUNTIME_BOOTSTRAP: Any | None = None

 EVENTS = {
     "SessionStart": {"startup": "agent.session.started", "resume": "agent.session.resumed", "compact": "agent.session.compacted"},
     "SessionEnd": {"default": "agent.session.ended"},
     "PostToolUse": {"default": "agent.command.completed"},
 }


-def core_module() -> Any:
-    return importlib.import_module("processforge")
+def runtime_bootstrap() -> Any:
+    global _RUNTIME_BOOTSTRAP
+    if _RUNTIME_BOOTSTRAP is None:
+        repo_root = Path(__file__).resolve().parents[2]
+        module_name = "processforge_core.bootstrap"
+        module = sys.modules.get(module_name)
+        if module is None:
+            bootstrap_path = repo_root / "src" / "processforge_core" / "bootstrap.py"
+            spec = importlib.util.spec_from_file_location(module_name, bootstrap_path)
+            if spec is None or spec.loader is None:
+                raise ImportError(f"could not load bootstrap module: {bootstrap_path}")
+            module = importlib.util.module_from_spec(spec)
+            sys.modules[module_name] = module
+            spec.loader.exec_module(module)
+        _RUNTIME_BOOTSTRAP = module.bootstrap_runtime(__file__)
+    return _RUNTIME_BOOTSTRAP


 def normalized_event(payload: dict[str, Any]) -> dict[str, Any] | None:
     hook = str(payload.get("hook_event_name") or "")
     mapping = EVENTS.get(hook)
     if not mapping:
         return None
     source = str(payload.get("source") or "startup")
     event_type = mapping.get(source) or mapping.get("default")
     cwd = str(payload.get("cwd") or "")
     session_id = str(payload.get("session_id") or "")
     if not event_type or not cwd or not session_id:
         return None
     tool_name = str(payload.get("tool_name") or "")
     data = {key: payload[key] for key in ("turn_id", "tool_name", "tool_use_id", "model", "permission_mode", "reason") if payload.get(key) not in (None, "")}
     if hook == "PostToolUse" and tool_name and tool_name != "Bash":
         event_type = "agent.tool.completed"
     return {
         "schema_version": 1,
         "event_type": event_type,
         "event_id": f"codex:{hook}:{session_id}:{payload.get('turn_id', '')}:{payload.get('tool_use_id', '')}",
         "project_root": cwd,
         "session_id": session_id,
         "agent_id": "codex",
         "source": {"adapter": "codex-hooks", "agent": "codex", "session_id": session_id},
         "payload": data,
     }


 def dispatch(payload: dict[str, Any]) -> dict[str, Any]:
     event = normalized_event(payload)
     if not event:
         return {"status": "ignored"}
-    core = core_module()
+    runtime = runtime_bootstrap()
+    core = runtime.core
+    host = runtime.host
+    service = runtime.service
     project_root = Path(str(event["project_root"])).expanduser()
     try:
         core.require_flow_root(project_root)
     except SystemExit:
         return {"status": "ignored", "reason": "not_processforge_project"}
-    from pf_runtime import host, service

     # Prefer the active Runtime so hook delivery shares its authenticated IPC,
     # lifecycle record and operator journal.  A hook must remain advisory: an
     # unavailable daemon must not fail or delay the Codex turn, so fall back to
     # the durable Host/Core path that was used before the daemon was started.
     workplace_root = core.resolve_workplace_root(None, project_root=project_root)
     try:
         with contextlib.redirect_stdout(io.StringIO()):
             exit_code = service.runtime_request(
                 argparse.Namespace(workplace=str(workplace_root), json=True),
                 core,
                 "/event",
                 event,
             )
         if exit_code == 0:
             return {"status": "delivered", "transport": "runtime"}
     except (OSError, SystemExit, ValueError):
         pass

     with contextlib.redirect_stdout(io.StringIO()):
         result = host.ingest_event(event, None, core)
     return {"status": "delivered", "transport": "ledger-fallback", **result}


 def main() -> int:
     try:
         payload = json.load(sys.stdin)
         result = dispatch(payload if isinstance(payload, dict) else {})
         # Codex treats stdout as hook-protocol output.  Observation hooks do
         # not need to steer a session, so leave stdout empty in normal use;
         # arbitrary diagnostic JSON is rejected as an invalid hook result.
         if os.environ.get("PF_CODEX_HOOK_DEBUG") == "1":
             print(json.dumps(result, ensure_ascii=False))
     except Exception as exc:  # hooks are observation, never a Codex failure point
         if os.environ.get("PF_CODEX_HOOK_DEBUG") == "1":
             print(json.dumps({"status": "ignored", "reason": type(exc).__name__}, ensure_ascii=False))
     return 0
diff --git a/tools/smoke_processforge_core_package_bootstrap.py b/tools/smoke_processforge_core_package_bootstrap.py
new file mode 100644
--- /dev/null
+++ b/tools/smoke_processforge_core_package_bootstrap.py
@@ -0,0 +1,95 @@
+#!/usr/bin/env python3
+"""Smoke-test the packaged bootstrap seam for direct-script runtime adapters."""
+
+from __future__ import annotations
+
+import importlib
+import importlib.util
+import json
+import os
+import subprocess
+import sys
+from pathlib import Path
+from typing import Any
+
+REPO_ROOT = Path(__file__).resolve().parents[1]
+
+
+def load_module(module_name: str, path: Path) -> Any:
+    module = sys.modules.get(module_name)
+    if module is not None:
+        return module
+    spec = importlib.util.spec_from_file_location(module_name, path)
+    if spec is None or spec.loader is None:
+        raise RuntimeError(f"could not load module: {path}")
+    module = importlib.util.module_from_spec(spec)
+    sys.modules[module_name] = module
+    spec.loader.exec_module(module)
+    return module
+
+
+def run_python(*args: str, input_text: str | None = None, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
+    env = os.environ.copy()
+    if extra_env:
+        env.update(extra_env)
+    return subprocess.run(
+        [sys.executable, *args],
+        cwd=str(REPO_ROOT),
+        input=input_text,
+        text=True,
+        capture_output=True,
+        env=env,
+        check=False,
+    )
+
+
+def main() -> int:
+    bootstrap = load_module("processforge_core.bootstrap", REPO_ROOT / "src" / "processforge_core" / "bootstrap.py")
+    runtime = bootstrap.bootstrap_runtime(__file__)
+    assert runtime.repo_root == REPO_ROOT
+    assert runtime.core.ROOT == REPO_ROOT
+    assert sys.modules["processforge_core._legacy_processforge"] is runtime.core
+    assert importlib.import_module("processforge") is runtime.core
+    assert runtime.host.__name__ == "pf_runtime.host"
+    assert runtime.service.__name__ == "pf_runtime.service"
+    assert runtime.service.host is runtime.host
+
+    adapter_runtime = bootstrap.bootstrap_runtime(REPO_ROOT / "tools" / "pf_runtime" / "mcp_server.py")
+    assert adapter_runtime.core is runtime.core
+
+    mcp_server = load_module("processforge_core_smoke_mcp_server", REPO_ROOT / "tools" / "pf_runtime" / "mcp_server.py")
+    codex_hooks = load_module("processforge_core_smoke_codex_hooks", REPO_ROOT / "tools" / "pf_runtime" / "codex_hooks.py")
+    assert mcp_server.runtime_bootstrap().core is runtime.core
+    assert mcp_server.runtime_bootstrap().host is runtime.host
+    assert codex_hooks.runtime_bootstrap().core is runtime.core
+    assert codex_hooks.runtime_bootstrap().service is runtime.service
+
+    mcp_help = run_python("tools/pf_runtime/mcp_server.py", "--workplace", str(REPO_ROOT), "--help")
+    assert mcp_help.returncode == 0, mcp_help.stderr
+
+    hook_payload = json.dumps(
+        {
+            "hook_event_name": "SessionStart",
+            "source": "startup",
+            "cwd": "C:/Windows",
+            "session_id": "smoke-session",
+            "turn_id": "t1",
+            "tool_name": "Bash",
+            "tool_use_id": "u1",
+        }
+    )
+    hook_debug = run_python(
+        "tools/pf_runtime/codex_hooks.py",
+        input_text=hook_payload,
+        extra_env={"PF_CODEX_HOOK_DEBUG": "1"},
+    )
+    assert hook_debug.returncode == 0, hook_debug.stderr
+    assert '"status": "ignored"' in hook_debug.stdout
+    assert '"reason": "not_processforge_project"' in hook_debug.stdout
+
+    print("ok")
+    return 0
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())
```

## Verification

- `python tools/smoke_processforge_core_package_bootstrap.py`
- `python bin/pf.py --help`
- `python tools/processforge.py --help`
- `@'{"jsonrpc":"2.0","id":1,"method":"initialize"} {"jsonrpc":"2.0","id":2,"method":"tools/list"}'@ | python tools/pf_runtime/mcp_server.py --workplace .`
- `$env:PF_CODEX_HOOK_DEBUG='1'; @'{"hook_event_name":"SessionStart","source":"startup","cwd":"C:/Windows","session_id":"smoke-session","turn_id":"t1","tool_name":"Bash","tool_use_id":"u1"}'@ | python tools/pf_runtime/codex_hooks.py`