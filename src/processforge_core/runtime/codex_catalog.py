"""Read model capabilities from the configured Codex App Server."""

from __future__ import annotations

import json
import os
import shutil
import time
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Full, Queue
from subprocess import Popen
from threading import Event, Thread
from typing import Any

from processforge_core.runtime.environment import WorkerEnvironmentPolicy

MAX_FRAME_BYTES = 1024 * 1024
MAX_PAGES = 20
PAGE_SIZE = 50
RPC_TIMEOUT_SECONDS = 10.0
MAX_CURSOR_LENGTH = 256

CatalogProcess = Callable[
    [list[str], Path, Mapping[str, str]], AbstractContextManager[Popen[bytes]]
]


class CatalogError(ValueError):
    """Report a public catalog failure without carrying native response text."""


@dataclass(frozen=True)
class CodexLaunchProfile:
    cwd: Path
    environment: dict[str, str]
    executable: str | None
    model: str
    effort: str

    @classmethod
    def from_command(
        cls, project_root: Path, command: dict[str, Any]
    ) -> CodexLaunchProfile:
        spec = command["command"]
        cwd = Path(spec.get("working_directory") or project_root).resolve()
        environment = WorkerEnvironmentPolicy().materialize(spec)
        model, effort = codex_preferences(environment)
        if (model or effort) and cwd != project_root:
            raise CatalogError("codex_profile_unavailable")
        # These receipt and input identifiers are assigned by PF after catalog
        # validation. They are separate from the Codex process configuration.
        for name in (
            "PF_WORKER_ATTEMPT",
            "PF_PREPARED_INPUT_FILE",
            "PF_PREPARED_INPUT_SHA256",
            "PF_AGENT_EXIT_PATH",
            "PF_CONFIGURATION_SNAPSHOT_PATH",
            "PF_CONFIGURATION_SNAPSHOT_SHA256",
        ):
            environment.pop(name, None)
        return cls(
            cwd, environment, resolve_codex_executable(environment, cwd), model, effort
        )

    def validate(self, launch: CatalogProcess) -> None:
        if not self.model and not self.effort:
            return
        if self.executable is None:
            raise CatalogError("codex_executable_unavailable")
        result = read_codex_catalog(
            self.cwd,
            self.environment,
            launch,
            include_hidden=True,
            executable=self.executable,
        )
        verify_codex_preferences(result, self.model, self.effort)


def codex_preferences(environment: Mapping[str, str]) -> tuple[str, str]:
    return (
        environment.get("PF_AGENT_MODEL") or environment.get("PF_CODEX_MODEL") or "",
        environment.get("PF_CODEX_REASONING_EFFORT") or "",
    )


def verify_codex_preferences(catalog: dict[str, Any], model: str, effort: str) -> None:
    """Require explicit selections to be supported by the effective agent."""
    if not model and not effort:
        return
    if catalog["status"] != "ready":
        raise CatalogError("codex_catalog_unknown")
    models = catalog["models"]
    if not model:
        defaults = catalog["configured_defaults"]
        if defaults["status"] != "ready":
            raise CatalogError("codex_default_model_unknown")
        model = defaults["model"]
        if model is None:
            marked = [item["model"] for item in models if item["is_default"]]
            if len(marked) != 1:
                raise CatalogError("codex_default_model_unknown")
            model = marked[0]
    matching = [item for item in models if item["model"] == model]
    if not matching:
        raise CatalogError("codex_model_unavailable")
    if effort:
        reported = [item["reasoning_efforts"] for item in matching]
        if any(options is not None and effort in options for options in reported):
            return
        if any(options is None for options in reported):
            raise CatalogError("codex_reasoning_effort_unknown")
        raise CatalogError("codex_reasoning_effort_unavailable")


def resolve_codex_executable(environment: Mapping[str, str], cwd: Path) -> str | None:
    explicit = environment.get("PF_CODEX_EXECUTABLE") or environment.get(
        "CODEX_EXECUTABLE"
    )
    path = environment.get("PATH", os.defpath)
    folders = [str(cwd / folder) for folder in path.split(os.pathsep)]
    if os.name == "nt":
        folders.insert(0, str(cwd))
    search_path = os.pathsep.join(folders)
    if explicit:
        if os.path.dirname(explicit):
            return str(cwd / explicit)
        return shutil.which(explicit, path=search_path) or explicit
    return shutil.which("codex", path=search_path) or shutil.which(
        "codex.cmd", path=search_path
    )


def is_codex_exec_driver(driver: dict[str, Any], distribution_root: Path) -> bool:
    command = driver.get("command")
    if driver.get("id") != "codex-exec" or not isinstance(command, dict):
        return False
    args = command.get("args")
    if command.get("executable") != "{python_executable}" or not args:
        return False
    if not isinstance(args, list) or not isinstance(args[0], str):
        return False
    wrapper = args[0].replace("{processforge_root}", str(distribution_root))
    return (
        Path(wrapper).resolve()
        == (distribution_root / "tools/codex_exec_worker.py").resolve()
    )


def describe_codex_driver(
    driver: dict[str, Any],
    project_root: Path,
    distribution_root: Path,
    launch: CatalogProcess,
) -> dict[str, Any]:
    if not is_codex_exec_driver(driver, distribution_root):
        return {"status": "unsupported"}
    policy = WorkerEnvironmentPolicy()
    spec = driver.get("environment") or {}
    if not isinstance(spec, dict):
        return {"status": "unknown", "reason": "codex_profile_unavailable"}
    variables = {
        "project_root": str(project_root),
        "processforge_root": str(distribution_root),
        "driver_id": "codex-exec",
    }
    try:
        cwd = Path(
            policy.expand(
                driver.get("working_directory") or "{project_root}", variables
            )
        ).resolve()
        declared = spec.get("variables") or {}
        if not isinstance(declared, dict):
            return {"status": "unknown", "reason": "codex_profile_unavailable"}
        # These two wrapper settings do not select the App Server profile.
        wrapper_settings = {"PF_CODEX_REASONING_EFFORT", "PF_CODEX_SANDBOX"}
        profile_variables = {
            key: value for key, value in declared.items() if key not in wrapper_settings
        }
        explicit = policy.expand(profile_variables, variables)
    except (OSError, TypeError, ValueError, SystemExit):
        return {"status": "unknown", "reason": "codex_profile_unavailable"}
    if cwd != project_root or not isinstance(explicit, dict):
        return {"status": "unknown", "reason": "codex_profile_unavailable"}
    environment = policy.materialize(
        {"environment": explicit, "environment_inherit": spec.get("inherit", True)}
    )
    return read_codex_catalog(project_root, environment, launch)


def _identifier(value: Any, limit: int = 256) -> str | None:
    if (
        isinstance(value, str)
        and 0 < len(value) <= limit
        and value == value.strip()
        and value.isprintable()
    ):
        return value
    return None


def _model(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise CatalogError("codex_catalog_invalid")
    model_id = _identifier(record.get("id"))
    launch_id = _identifier(record.get("model"))
    if model_id is None or launch_id is None:
        raise CatalogError("codex_catalog_invalid")

    options = record.get("supportedReasoningEfforts")
    efforts: list[str] | None = None
    if isinstance(options, list):
        parsed = [
            _identifier(option.get("reasoningEffort"), 128)
            if isinstance(option, dict)
            else None
            for option in options
        ]
        if all(option is not None for option in parsed):
            efforts = list(
                dict.fromkeys(option for option in parsed if option is not None)
            )
    return {
        "id": model_id,
        "model": launch_id,
        "reasoning_efforts": efforts,
        "default_reasoning_effort": _identifier(
            record.get("defaultReasoningEffort"), 128
        ),
        "is_default": record.get("isDefault") is True,
        "hidden": record.get("hidden") is True,
    }


class CodexCatalogClient:
    """Call the Codex catalog over a bounded stdio session."""

    def __init__(self, process: Popen[bytes], deadline: float) -> None:
        self.process = process
        self.deadline = deadline
        self.frames: Queue[bytes | CatalogError] = Queue(maxsize=4)
        self.finished = Event()
        self.request_id = 0
        self.reader = Thread(target=self._read, daemon=True)

    def _emit(self, frame: bytes | CatalogError) -> None:
        while not self.finished.is_set():
            try:
                self.frames.put(frame, timeout=0.1)
                return
            except Full:
                continue

    def _read(self) -> None:
        source = self.process.stdout
        if source is None:
            self._emit(CatalogError("codex_catalog_unavailable"))
            return
        try:
            while not self.finished.is_set():
                frame = source.readline(MAX_FRAME_BYTES + 1)
                if not frame:
                    break
                if len(frame) > MAX_FRAME_BYTES:
                    self._emit(CatalogError("codex_catalog_response_limit"))
                    return
                self._emit(frame)
        except (OSError, ValueError):
            pass
        self._emit(CatalogError("codex_catalog_closed"))

    def _remaining(self) -> float:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise CatalogError("codex_catalog_timeout")
        return remaining

    def _send(self, message: dict[str, Any]) -> None:
        target = self.process.stdin
        if target is None:
            raise CatalogError("codex_catalog_unavailable")
        encoded = json.dumps(message).encode("utf-8") + b"\n"
        written: Queue[bool] = Queue(maxsize=1)

        def write() -> None:
            try:
                target.write(encoded)
                target.flush()
            except (OSError, ValueError):
                written.put(False)
            else:
                written.put(True)

        self._remaining()
        Thread(target=write, daemon=True).start()
        try:
            if not written.get(timeout=self._remaining()):
                raise CatalogError("codex_catalog_closed")
        except Empty as exc:
            raise CatalogError("codex_catalog_timeout") from exc

    def _call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.request_id += 1
        request_id = self.request_id
        self._send({"id": request_id, "method": method, "params": params})
        while True:
            try:
                frame = self.frames.get(timeout=self._remaining())
            except Empty as exc:
                raise CatalogError("codex_catalog_timeout") from exc
            if isinstance(frame, CatalogError):
                raise frame
            try:
                response = json.loads(frame.decode("utf-8"))
            except (UnicodeError, ValueError, RecursionError) as exc:
                raise CatalogError("codex_catalog_invalid") from exc
            if not isinstance(response, dict):
                raise CatalogError("codex_catalog_invalid")
            response_id = response.get("id")
            if type(response_id) is not int or response_id != request_id:
                continue
            if "error" in response:
                raise CatalogError("codex_catalog_request_failed")
            result = response.get("result")
            if isinstance(result, dict):
                return result
            raise CatalogError("codex_catalog_invalid")

    def initialize(self) -> None:
        self.reader.start()
        self._call(
            "initialize",
            {"clientInfo": {"name": "processforge", "version": "1"}},
        )
        self._send({"method": "initialized", "params": {}})

    def catalog(self, *, include_hidden: bool = False) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"includeHidden": include_hidden, "limit": PAGE_SIZE}
        models: list[dict[str, Any]] = []
        seen_cursors: set[str] = set()
        for _ in range(MAX_PAGES):
            page = self._call("model/list", params)
            entries = page.get("data")
            if not isinstance(entries, list):
                raise CatalogError("codex_catalog_invalid")
            if len(entries) > PAGE_SIZE:
                raise CatalogError("codex_catalog_response_limit")
            models.extend(_model(entry) for entry in entries)
            cursor = page.get("nextCursor")
            if cursor is None:
                return models
            if (
                not isinstance(cursor, str)
                or not 0 < len(cursor) <= MAX_CURSOR_LENGTH
                or cursor in seen_cursors
            ):
                raise CatalogError("codex_catalog_pagination_invalid")
            seen_cursors.add(cursor)
            params["cursor"] = cursor
        raise CatalogError("codex_catalog_pagination_limit")

    def configured_defaults(self, cwd: Path) -> dict[str, Any]:
        try:
            result = self._call(
                "config/read", {"cwd": str(cwd), "includeLayers": False}
            )
            config = result.get("config")
            if not isinstance(config, dict):
                raise CatalogError("codex_profile_unavailable")
        except CatalogError as exc:
            return {"status": "unknown", "reason": str(exc)}
        model = _identifier(config.get("model"))
        effort = _identifier(config.get("model_reasoning_effort"), 128)
        if (model is None and config.get("model") is not None) or (
            effort is None and config.get("model_reasoning_effort") is not None
        ):
            return {"status": "unknown", "reason": "codex_profile_unavailable"}
        return {
            "status": "ready",
            "model": model,
            "reasoning_effort": effort,
        }


def read_codex_catalog(
    cwd: Path,
    environment: Mapping[str, str],
    launch: CatalogProcess,
    *,
    include_hidden: bool = False,
    timeout: float = RPC_TIMEOUT_SECONDS,
    executable: str | None = None,
) -> dict[str, Any]:
    executable = executable or resolve_codex_executable(environment, cwd)
    if executable is None:
        return {"status": "unknown", "reason": "codex_executable_unavailable"}
    client: CodexCatalogClient | None = None
    try:
        deadline = time.monotonic() + timeout
        with launch([executable, "app-server"], cwd, environment) as process:
            client = CodexCatalogClient(process, deadline)
            try:
                client.initialize()
                models = client.catalog(include_hidden=include_hidden)
                defaults = client.configured_defaults(cwd)
            finally:
                client.finished.set()
    except CatalogError as exc:
        return {"status": "unknown", "reason": str(exc)}
    except OSError:
        return {"status": "unknown", "reason": "codex_catalog_unavailable"}
    finally:
        if client is not None and client.reader.is_alive():
            client.reader.join(timeout=1)
    return {"status": "ready", "models": models, "configured_defaults": defaults}
