"""Disposable Windows controlled-origin issuer; never provision a workstation.

The broker accepts no requests. It runs one source-defined suite with fixed
argv and protocol bodies. Legacy and current workloads are trusted code under
the maintenance principal. Ordinary callers cannot access the fixture at all.
This does not qualify arbitrary worker programs or unknown historical origins.
"""

from __future__ import annotations

import ctypes
import json
import os
import secrets
import shutil
import subprocess
import sys
from contextlib import contextmanager
from ctypes import wintypes
from pathlib import Path
from typing import Any, Iterator


def require_disposable_ci() -> None:
    if not (
        os.name == "nt"
        and os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
    ):
        raise RuntimeError("disposable_github_hosted_windows_runner_required")


def powershell(script: str, data: dict[str, Any]) -> str:
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NonInteractive",
            "-NoProfile",
            "-Command",
            '$ErrorActionPreference = "Stop"; '
            "$p = [Console]::In.ReadToEnd() | ConvertFrom-Json; try { "
            + script
            + " } catch { [Console]::Error.Write((@{"
            "exception=$_.Exception.GetType().FullName;"
            "hresult=$_.Exception.HResult;error_id=$_.FullyQualifiedErrorId"
            "} | ConvertTo-Json -Compress)); exit 1 }",
        ],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=90,
        check=False,
    )
    if result.returncode:
        # Do not echo shell bodies, passwords or private machine information.
        try:
            failure = json.loads(result.stderr)
        except json.JSONDecodeError:
            failure = {"error_id": "powershell_unstructured_failure"}
        raise RuntimeError(
            "fixture_provisioning_failed_exit_"
            + str(result.returncode)
            + ":"
            + json.dumps(failure)
        )
    return result.stdout.strip()


@contextmanager
def ordinary_token(user: str, password: str) -> Iterator[Any]:
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi.LogonUserW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    advapi.LogonUserW.restype = wintypes.BOOL
    advapi.ImpersonateLoggedOnUser.argtypes = [wintypes.HANDLE]
    advapi.ImpersonateLoggedOnUser.restype = wintypes.BOOL
    advapi.RevertToSelf.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    token = wintypes.HANDLE()
    if not advapi.LogonUserW(user, ".", password, 2, 0, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not advapi.ImpersonateLoggedOnUser(token):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            yield token
        finally:
            if not advapi.RevertToSelf():
                # Continuing a trusted issuer while impersonated is forbidden.
                raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(token)


def denied(path: Path, access: int) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateFileW(str(path), access, 7, None, 3, 0x02000000, None)
    if handle != wintypes.HANDLE(-1).value:
        kernel.CloseHandle(handle)
        raise RuntimeError("ordinary_principal_has_forbidden_effective_access")
    if ctypes.get_last_error() != 5:
        raise ctypes.WinError(ctypes.get_last_error())


def protected_directory(path: Path, maintenance_sid: str) -> None:
    """Create the genesis root with its protected DACL atomically, or refuse."""
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)

    class SecurityAttributes(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.DWORD),
            ("descriptor", ctypes.c_void_p),
            ("inherit", wintypes.BOOL),
        ]

    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    kernel.CreateDirectoryW.argtypes = [
        wintypes.LPCWSTR,
        ctypes.POINTER(SecurityAttributes),
    ]
    kernel.CreateDirectoryW.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    descriptor = ctypes.c_void_p()
    sddl = "D:P(A;OICI;FA;;;" + maintenance_sid + ")(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)"
    if not advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        sddl, 1, ctypes.byref(descriptor), None
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        attributes = SecurityAttributes(
            ctypes.sizeof(SecurityAttributes), descriptor, False
        )
        # Unlike mkdir then Set-Acl, there is no initially accessible object and
        # no possibility of editing an already existing or substituted root.
        if not kernel.CreateDirectoryW(str(path), ctypes.byref(attributes)):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.LocalFree(descriptor)


def qualify_access(root: Path, user: str, password: str) -> dict[str, Any]:
    # One protected ancestor excludes alternate CLI/runtime/MCP/worker starts
    # and direct writes. Check ancestor replacement rights independently.
    objects = [root, *root.rglob("*")]
    for path in objects:
        info = path.lstat()
        if getattr(info, "st_file_attributes", 0) & 0x400 or path.is_symlink():
            raise RuntimeError("fixture_reparse_object_refused")
    with ordinary_token(user, password):
        for parent in root.parents:
            for access in (0x40, 0x40000, 0x80000):
                denied(parent, access)
        for path in objects:
            for access in (1, 2, 0x10000, 0x40000, 0x80000):
                denied(path, access)
    return {
        "effective_access": "denied",
        "object_count": len(objects),
        "ordinary_principal": user,
        "model": "fixed-trusted-workload-broker-v1",
    }


def runtime_probe() -> int:
    """Probe the copied interpreter and real loaded DLLs before legacy genesis."""
    import importlib

    request = json.loads(sys.stdin.read())
    runtime = Path(sys.prefix).resolve()
    assert Path(sys.executable).resolve() == runtime / "python.exe"
    for name in (
        "_sqlite3",
        "_ssl",
        "_hashlib",
        "_socket",
        "_bz2",
        "_lzma",
        "unicodedata",
        "_elementtree",
        "_ctypes",
        "select",
        "yaml",
        "jsonschema",
    ):
        importlib.import_module(name)
    assert all(Path(p).resolve().is_relative_to(runtime) for p in sys.path if p)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.K32EnumProcessModules.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.HMODULE),
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel.K32EnumProcessModules.restype = wintypes.BOOL
    kernel.K32GetModuleFileNameExW.argtypes = [
        wintypes.HANDLE,
        wintypes.HMODULE,
        wintypes.LPWSTR,
        wintypes.DWORD,
    ]
    kernel.K32GetModuleFileNameExW.restype = wintypes.DWORD
    modules = (wintypes.HMODULE * 4096)()
    needed = wintypes.DWORD()
    process = kernel.GetCurrentProcess()
    assert kernel.K32EnumProcessModules(
        process, modules, ctypes.sizeof(modules), ctypes.byref(needed)
    )
    assert needed.value <= ctypes.sizeof(modules)
    paths = []
    system = Path(os.environ["SystemRoot"]).resolve()
    for index in range(needed.value // ctypes.sizeof(wintypes.HMODULE)):
        buffer = ctypes.create_unicode_buffer(32768)
        length = kernel.K32GetModuleFileNameExW(
            process, modules[index], buffer, len(buffer)
        )
        assert 0 < length < len(buffer)
        path = Path(buffer.value).resolve(strict=True)
        assert path.is_relative_to(runtime) or path.is_relative_to(system), (
            "external_native_module"
        )
        paths.append(path)
    with ordinary_token(request["user"], request["password"]):
        for path in paths:
            for access in (2, 0x10000, 0x40000, 0x80000):
                denied(path, access)
            for parent in path.parents:
                if parent.is_relative_to(runtime):
                    continue  # Already checked through the protected namespace.
                for access in (0x40, 0x40000, 0x80000):
                    denied(parent, access)
    import hashlib

    print(
        json.dumps(
            {
                "sys_path": sys.path,
                "python": sys.version,
                "windows": sys.getwindowsversion()[:],
                "loaded_modules": [
                    {
                        "path": str(p),
                        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    }
                    for p in paths
                ],
                "effective_module_write_access": "denied",
            }
        )
    )
    return 0


def provision(args: Any) -> int:
    """Bootstrap before *any* old payload execution, in a new CI namespace."""
    require_disposable_ci()
    from smoke_public_core_upgrade import (
        PUBLIC_COMMIT,
        PUBLIC_SIDECAR_SHA256,
        PUBLIC_ZIP_SHA256,
        sha256,
        verify_archive,
    )

    root, out = args.root.resolve(), args.out.resolve()
    if root.exists() or out.exists():
        raise RuntimeError("new_fixture_and_evidence_roots_required")
    public = args.public_dir.resolve()
    old_zip = public / "processforge-1.2.0.zip"
    old_sidecar = public / "processforge-1.2.0.manifest.json"
    assert sha256(old_sidecar.read_bytes()) == PUBLIC_SIDECAR_SHA256
    verify_archive(old_zip, old_sidecar, PUBLIC_ZIP_SHA256, PUBLIC_COMMIT)
    candidate = args.candidate.resolve()
    verify_archive(candidate, args.sidecar.resolve(), args.sha256, args.commit)
    root.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True)
    user, password = "pfci" + secrets.token_hex(6), secrets.token_urlsafe(40) + "Aa1!"
    created = False
    receipt: dict[str, Any] = {"status": "provisioning", "full_t06_qualified": False}
    try:
        identities = json.loads(
            powershell(
                "$u = New-LocalUser -Name $p.user -Password "
                "(ConvertTo-SecureString $p.password -AsPlainText -Force) "
                "-AccountNeverExpires; "
                "$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value; "
                "@{ordinary=$u.SID.Value;maintenance=$sid} | ConvertTo-Json -Compress",
                {"user": user, "password": password},
            )
        )
        created = True
        powershell(
            '$group = New-Object System.Security.Principal.SecurityIdentifier("S-1-5-32-545"); '
            "$u = Get-LocalUser -Name $p.user; "
            "if (-not (Get-LocalGroupMember -SID $group | Where-Object { $_.SID -eq $u.SID })) { "
            "Add-LocalGroupMember -SID $group -Member $u }",
            {"user": user},
        )
        protected_directory(root, identities["maintenance"])
        runtime = root / "runtime"
        shutil.copytree(
            Path(sys.base_prefix),
            runtime,
            ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "Doc", "include", "libs", "tcl", "Scripts"
            ),
        )
        # No external site/startup path may survive the runtime copy.
        for path in runtime.rglob("*.pth"):
            path.unlink()
        for name in ("sitecustomize.py", "usercustomize.py", "pyvenv.cfg"):
            if list(runtime.rglob(name)):
                raise RuntimeError("runtime_startup_customization_refused")
        import zipfile

        manager, core = root / "manager", root / "core"
        with zipfile.ZipFile(candidate) as bundle:
            bundle.extractall(manager)
        with zipfile.ZipFile(old_zip) as bundle:
            bundle.extractall(core)
        control, project, workplace, device, temp = (
            root / name
            for name in ("control", "project", "workplace", "device", "temp")
        )
        for directory in (control, project, workplace, device, temp):
            directory.mkdir()
        for source in (old_zip, old_sidecar, candidate, args.sidecar.resolve()):
            shutil.copyfile(source, control / source.name)
        access = qualify_access(root, user, password)
        receipt.update(status="provisioned", access=access, identities=identities)
        # This body is issued by bootstrap before old history. The digest only
        # binds its evidence; profile construction is not the trust root.
        (control / "qualification.json").write_text(
            json.dumps(receipt), encoding="utf-8"
        )
        command = [
            str(runtime / "python.exe"),
            "-I",
            "-B",
            str(manager / "tools/smoke_public_core_upgrade.py"),
            "--controlled-original-run",
            "--root",
            str(root),
            "--out",
            str(out),
            "--public-dir",
            str(control),
            "--candidate",
            str(control / candidate.name),
            "--sidecar",
            str(control / args.sidecar.name),
            "--sha256",
            args.sha256,
            "--commit",
            args.commit,
            "--controlled-fault",
            args.controlled_fault,
        ]
        environment = {
            "SystemRoot": os.environ["SystemRoot"],
            "WINDIR": os.environ["SystemRoot"],
            "PATH": str(runtime)
            + os.pathsep
            + str(Path(os.environ["SystemRoot"]) / "System32"),
            "TEMP": str(temp),
            "TMP": str(temp),
            "TMPDIR": str(temp),
            "LOCALAPPDATA": str(device),
            "APPDATA": str(device),
            "USERPROFILE": str(device),
            "XDG_CONFIG_HOME": str(device),
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "GITHUB_ACTIONS": "true",
            "RUNNER_ENVIRONMENT": "github-hosted",
        }
        probe = subprocess.run(
            [
                str(runtime / "python.exe"),
                "-I",
                "-B",
                str(manager / "tools/pf_controlled_upgrade_ci.py"),
                "--runtime-probe",
            ],
            input=json.dumps({"user": user, "password": password}),
            env=environment,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=90,
            check=False,
        )
        receipt["runtime_probe_exit"] = probe.returncode
        if probe.returncode:
            # This stream has no credentials; preserve the actual privilege or
            # runtime failure for the runner owner.
            (out / "runtime-probe.stderr.log").write_text(
                probe.stderr, encoding="utf-8"
            )
            raise RuntimeError("copied_runtime_qualification_failed")
        receipt["runtime_probe"] = json.loads(probe.stdout)
        receipt["runtime_closure"] = [
            {"path": str(p), "sha256": sha256(p.read_bytes())}
            for p in sorted(runtime.rglob("*"))
            if p.is_file()
        ]
        (control / "qualification.json").write_text(
            json.dumps(receipt), encoding="utf-8"
        )
        result = subprocess.run(
            command,
            env=environment,
            cwd=root,
            capture_output=True,
            timeout=900,
            check=False,
        )
        (out / "manager.stdout.log").write_bytes(result.stdout)
        (out / "manager.stderr.log").write_bytes(result.stderr)
        receipt["manager_exit"] = result.returncode
        if result.returncode:
            raise RuntimeError("controlled_original_manager_failed")
        receipt["status"] = "suite_passed"
        return 0
    except Exception as error:
        receipt["exception"] = type(error).__name__
        receipt["winerror"] = getattr(error, "winerror", None)
        receipt["errno"] = getattr(error, "errno", None)
        if isinstance(error, RuntimeError):
            receipt["reason"] = str(error)
        raise
    finally:
        (out / "issuer.json").write_text(
            json.dumps(receipt, indent=2), encoding="utf-8"
        )
        if created:
            powershell("Remove-LocalUser -Name $p.user", {"user": user})


def install_echo_driver(project: Path, manager: Path, executable: str) -> None:
    """Install the one trusted driver in this protected fixture, before old work."""
    driver = project / ".pf/runtime/drivers/controlled-echo.yaml"
    driver.parent.mkdir(parents=True, exist_ok=True)
    # The trusted worker has a single output and no code/plugin input.
    worker = project / ".pf/runtime/controlled-echo.py"
    worker.write_bytes((manager / "tools/pf_controlled_echo_worker.py").read_bytes())
    driver.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": "controlled-echo",
                "title": "Controlled echo",
                "kind": "shell",
                "prepared_lifecycle_wrapper": True,
                "command": {
                    "executable": executable,
                    "args": ["-I", "-B", str(worker), "{expected_report_path}"],
                    "model_args": [],
                },
                "working_directory": "{project_root}",
                "environment": {"inherit": True, "variables": {}},
                "io": {
                    "stdin": "none",
                    "stdout": ".pf/runtime/agent-runs/{run_id}/{task_id}/stdout.log",
                    "stderr": ".pf/runtime/agent-runs/{run_id}/{task_id}/stderr.log",
                },
                "heartbeat": {
                    "mode": "file",
                    "path": ".pf/runtime/agent-runs/{run_id}/{task_id}/heartbeat.json",
                    "optional": True,
                },
                "limits": {"timeout_seconds": 30, "max_retries": 0},
                "security": {
                    "allow_shell": False,
                    "require_explicit_executable": True,
                    "allow_network": False,
                },
            }
        ),
        encoding="utf-8",
    )
    registry = project / ".pf/runtime/registries/runtime-drivers.local.yaml"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "runtime_drivers": [
                    {
                        "id": "controlled-echo",
                        "path": "../drivers/controlled-echo.yaml",
                        "status": "available",
                        "builtin": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def run_suite(args: Any) -> int:
    """Actual accepted manager, constructed before the first genuine old writer."""
    require_disposable_ci()
    import io
    import sqlite3
    import time
    from contextlib import redirect_stdout

    root, out = args.root.resolve(), args.out.resolve()
    runtime, manager, core, control, project, workplace, device = (
        root / n
        for n in (
            "runtime",
            "manager",
            "core",
            "control",
            "project",
            "workplace",
            "device",
        )
    )
    if (
        Path(sys.executable).resolve() != runtime / "python.exe"
        or Path(sys.prefix).resolve() != runtime
    ):
        raise RuntimeError("qualified_runtime_required")
    qualification = json.loads((control / "qualification.json").read_bytes())
    assert qualification["status"] == "provisioned"
    assert qualification["access"]["effective_access"] == "denied"
    sys.path[:0] = [str(manager / "tools"), str(manager / "src")]
    # Trust is the candidate pin from bootstrap, followed by sealed capture.
    from smoke_public_core_upgrade import sha256, snapshot, verify_archive

    verify_archive(args.candidate, args.sidecar, args.sha256, args.commit)
    import importlib

    # Use the real public entry bootstrap to capture the native leaf and image.
    # A plain library import cannot promote itself to sealed entry authority.
    importlib.import_module("processforge")
    import pf_native_control as native

    entry = native.current_entry()
    assert entry is not None and entry.root == manager and entry.publication is not None
    from processforge_core.composition import (
        build_configuration_provider,
        build_storage_migration_host,
    )
    from processforge_core.maintenance.original_manager_update import (
        OriginalManagerUpdateService,
        OriginalRelease,
        original_update_succeeded,
    )

    release = OriginalRelease.public_1_2(
        (control / "processforge-1.2.0.zip").read_bytes(),
        (control / "processforge-1.2.0.manifest.json").read_bytes(),
    )
    report: dict[str, Any] = {
        "status": "running",
        "full_t06_qualified": False,
        "source_commit": args.commit,
        "archive_sha256": args.sha256,
        "commands": [],
        "matrix": {},
        "principal_model": qualification["access"]["model"],
    }

    def save() -> None:
        (out / "controlled-original.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )

    environment = dict(os.environ)
    environment.pop("PF_NATIVE_JOB_HANDLE", None)
    environment.pop("PF_NATIVE_JOB_NAME", None)
    executable = str(runtime / "python.exe")
    cli = [executable, "-I", "-B", str(core / "bin/pf.py")]
    scope = control / "scope.json"
    scope.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "assignment": {
                    "allowed_actions": ["read", "write_artifact"],
                    "forbidden_actions": ["write_product"],
                    "allowed_read_files": ["README.md", ".pf/**"],
                    "allowed_files": [".pf/artifacts/controlled/**"],
                    "required_sources": ["README.md"],
                    "execution_mode": "docs_only",
                    "ownership": {"owner_id": "controlled-fixture", "writer": True},
                    "expected_report": {
                        "artifact": ".pf/artifacts/controlled/report.md",
                        "format": "markdown",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    old_scope = control / "scope-old-worker.json"
    old_scope_document = json.loads(scope.read_bytes())
    old_scope_document["assignment"]["allowed_files"] = [
        ".pf/artifacts/controlled-old/**"
    ]
    old_scope_document["assignment"]["expected_report"]["artifact"] = (
        ".pf/artifacts/controlled-old/report.md"
    )
    old_scope_document["assignment"]["ownership"]["owner_id"] = "controlled-old-fixture"
    old_scope.write_text(json.dumps(old_scope_document), encoding="utf-8")
    (project / "README.md").write_text("# Genuine retained project\n", encoding="utf-8")
    old_commands = [
        ["version"],
        [
            "workplace-init",
            "--workplace",
            str(workplace),
            "--profile",
            "software-development",
            "--apply",
        ],
        [
            "project-init",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--type",
            "processforge-development",
            "--process",
            "software-feature-development",
            "--apply",
        ],
        [
            "work-start",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--objective",
            "Genuine old worker history",
            "--process-id",
            "software-feature-development",
            "--scope-file",
            str(old_scope),
            "--json",
        ],
        ["runtime", "stop", "--workplace", str(workplace), "--timeout", "15"],
    ]
    old_commands.append(
        [
            "work-start",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--objective",
            "Controlled original release history",
            "--process-id",
            "software-feature-development",
            "--scope-file",
            str(scope),
            "--json",
        ]
    )
    routes = {
        "cli": [cli + command for command in old_commands],
        "runtime": [
            cli
            + ["runtime", "serve", "--workplace", str(workplace), "--interval", "3600"]
        ],
        "hook": [
            cli
            + [
                "hooks-dispatch",
                "--project-root",
                str(project),
                "--event-type",
                "assignment.created",
                "--outbox",
            ]
        ],
        "worker": [
            [
                executable,
                "-I",
                "-B",
                str(core / "tools/pf_runtime/mcp_server.py"),
                "--workplace",
                str(workplace),
                "--session",
                "controlled-worker",
            ]
        ],
        "updater": [cli + ["core-update", "status", "--core-root", str(core)]],
        "mcp": [
            [
                executable,
                "-I",
                "-B",
                str(core / "tools/pf_runtime/mcp_server.py"),
                "--workplace",
                str(workplace),
                "--session",
                "controlled",
            ]
        ],
    }
    closure = qualification["runtime_closure"]

    def verify_runtime_closure() -> None:
        assert {str(p) for p in runtime.rglob("*") if p.is_file()} == {
            row["path"] for row in closure
        }
        assert all(
            sha256(Path(row["path"]).read_bytes()) == row["sha256"] for row in closure
        )
        assert all(
            sha256(Path(row["path"]).read_bytes()) == row["sha256"]
            for row in qualification["runtime_probe"]["loaded_modules"]
        )

    verify_runtime_closure()
    # The issuer protects and pins the FULL closure in its qualification body.
    # The native descriptor needs only the executable for exact argv checks.
    # Ordinary tokens have no runtime write access; this broker has no caller
    # endpoint and its fixed trusted commands never mutate runtime. Rehashing
    # every dependency per copied Core file would add no principal guarantee.
    profile = {
        "release_sha256": sha256(release.archive),
        "sidecar_sha256": sha256(release.sidecar),
        "profile": sha256((control / "qualification.json").read_bytes()),
        "runtime": [
            {"path": executable, "sha256": sha256(Path(executable).read_bytes())}
        ],
        "routes": routes,
        "environment": environment,
        "cwd": str(root),
        "roots": list(
            map(
                str,
                (project, workplace, device, control, root / "temp", manager, runtime),
            )
        ),
    }
    guard, epoch = control / "original.guard", control / "original.epoch"
    guard.write_bytes(b"0")
    epoch.write_text("controlled-original-v1", encoding="ascii")
    boundary = native.LegacyManagedBoundary(
        core,
        existing_gate=native.NativeControl(guard, epoch, "controlled-original-v1"),
        accepted_archive=release.members,
        original_profile=profile,
    )
    report["source_tree"] = json.loads(args.sidecar.read_bytes())["source"]["tree"]
    report["physical_roots"] = {
        str(p.relative_to(root)): [p.stat().st_dev, p.stat().st_ino]
        for p in (core, manager, runtime, control, project, workplace, device)
    }
    (out / "first-writer-profile.json").write_text(
        json.dumps(profile, indent=2), encoding="utf-8"
    )
    save()

    def launch(argv: list[str], ingress: str) -> Any:
        return boundary.launch(
            argv,
            ingress=ingress,
            cwd=root,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def collect(
        label: str, process: Any, body: bytes = b"", expected: int | None = 0
    ) -> bytes:
        stdout, stderr = process.communicate(body, timeout=150)
        (out / (label + ".stdout.log")).write_bytes(stdout)
        (out / (label + ".stderr.log")).write_bytes(stderr)
        deadline = time.monotonic() + 10
        while process.native_job.active() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert process.native_job.active() == 0, "descendant retirement not proven"
        report["commands"].append(
            {
                "id": label,
                "pid": process.pid,
                "exit": process.returncode,
                "native_facts": process.native_facts,
            }
        )
        save()
        if expected is not None:
            assert process.returncode == expected, label
        return stdout

    def old(index: int) -> bytes:
        return collect("old-" + str(index), launch(routes["cli"][index], "cli"))

    def update(command: str, confirm: bool = False) -> tuple[int, dict[str, Any]]:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = service.public_cli(command, args.candidate, confirm=confirm)
        raw = stream.getvalue()
        (out / (command + "-" + str(len(report["commands"])) + ".json")).write_text(
            raw, encoding="utf-8"
        )
        report["commands"].append({"id": command, "exit": code})
        save()
        return code, json.loads(raw)

    try:
        old(0)
        old(1)
        old(2)
        install_echo_driver(project, manager, executable)
        old_work = json.loads(old(3))
        assert old_work["action"] == "created_new"
        report["old_work"] = old_work
        # Genuine old public MCP worker APIs carry exact returned selectors.
        # Bodies are finite trusted requests; no caller supplies driver/code.
        for operation in ("prepare", "start", "collect", "status"):
            arguments = {
                "project_root": str(project),
                "run_id": old_work["run_id"],
                "assignment_id": old_work["assignment_id"],
                "context_id": old_work["context"]["id"],
                "apply": True,
            }
            if operation in {"prepare", "start"}:
                arguments["driver"] = "controlled-echo"
            requests = [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "pf.worker." + operation,
                        "arguments": arguments,
                    },
                },
            ]
            replies = collect(
                "old-worker-" + operation,
                launch(routes["worker"][0], "worker"),
                ("\n".join(map(json.dumps, requests)) + "\n").encode(),
            )
            rows = [json.loads(line) for line in replies.splitlines()]
            assert len(rows) == 2 and "error" not in rows[1]
            assert rows[1]["result"].get("isError") is not True
            worker_result = json.loads(rows[1]["result"]["content"][0]["text"])
            assert worker_result["native_exit_code"] == 0
        old_output = project / ".pf/artifacts/controlled-old/report.md"
        assert (
            old_output.read_text(encoding="utf-8") == "Controlled worker completed.\n"
        )
        report["matrix"]["genuine_old_worker_history"] = "pass"
        work = json.loads(old(5))
        assert work["action"] == "created_new"
        report["work"] = work
        for ingress in ("hook", "updater"):
            collect("old-" + ingress, launch(routes[ingress][0], ingress))
        mcp_body = b'{"jsonrpc":"2.0","id":1,"method":"initialize"}\n{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n'
        replies = collect("old-mcp", launch(routes["mcp"][0], "mcp"), mcp_body)
        assert len([json.loads(line) for line in replies.splitlines()]) == 2

        from processforge_core.configuration import DeviceConfigurationSource

        device_config = DeviceConfigurationSource.default_path()
        assert device_config.is_relative_to(device)
        if not device_config.exists():
            device_config.parent.mkdir(parents=True, exist_ok=True)
            device_config.write_text("schema_version: 1\n", encoding="utf-8")
        provider = build_configuration_provider(
            project_root=project,
            workplace_root=workplace,
            device_config_path=device_config,
        )
        host = build_storage_migration_host(
            project_root=project,
            workplace_root=workplace,
            device_config_path=device_config,
            configuration=provider,
        )
        assert host.service._native_selection is not None
        selection = host.service._native_selection()
        service = OriginalManagerUpdateService(boundary, release, selection=selection)

        running = launch(routes["runtime"][0], "runtime")
        # Readiness is a real runtime publication, not a fabricated profile bit.
        service_file = workplace / "runtime/pf-runtime/service.json"
        deadline = time.monotonic() + 20
        while (
            not service_file.exists()
            and running.poll() is None
            and time.monotonic() < deadline
        ):
            time.sleep(0.05)
        assert service_file.exists() and running.poll() is None
        with boundary.held():
            assert boundary.facts()[0] == "active"
        core_before_live_refusal = snapshot(core)
        assert update("plan")[0] == 1
        assert snapshot(core) == core_before_live_refusal
        assert not (project / ".pf/data/execution-storage.json").exists()
        old(4)
        collect("old-runtime", running)
        with boundary.held():
            assert boundary.facts()[0] == "proven"
        report["matrix"]["all_six_ingress_retired"] = "pass"

        # Runtime stop may have changed its actual selection metadata.
        selection = host.service._native_selection()
        service = OriginalManagerUpdateService(boundary, release, selection=selection)
        report["selection"] = selection.document()
        identities_before = {
            str(p.relative_to(root)): sha256(p.read_bytes())
            for p in root.rglob("identity.json")
        }
        history = {
            str(p.relative_to(project)): p.read_bytes()
            for directory in ("assignments", "runs", "contexts")
            for p in (project / ".pf" / directory).rglob("*")
            if p.is_file()
        }
        from processforge_core.database import (
            Database,
            DatabaseIdentity,
            DatabaseTarget,
            SchemaManager,
            SQLiteDriver,
        )

        storage_context = host.context

        def store_identity(target: Any) -> Any:
            database = Database(
                SQLiteDriver(),
                DatabaseTarget(
                    target.target, DatabaseIdentity(None, target.scope, target.owner_id)
                ),
            )
            return SchemaManager().inspect(database, ()).identity

        stores_before = {
            str(t.target): store_identity(t) for t in storage_context.targets
        }
        (core / "LICENSE").write_bytes(b"local Core drift\n")
        (core / "NOTICE").unlink()
        sentinels = {
            "unknown-user.bin": b"unknown\x00",
            ".pf/private-history.json": b'{"keep":true}',
        }
        for name, raw in sentinels.items():
            path = core / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        before = snapshot(core)
        code, planned = update("plan")
        assert code == 0 and not planned["blockers"]
        assert (
            "LICENSE" in planned["locally_modified"]
            and "NOTICE" in planned["missing_owned"]
        )
        assert snapshot(core) == before
        try:
            service.core_update("plan", args.candidate, workplace_root=root / "temp")
        except Exception as error:
            assert getattr(error, "code", None) == "plan_blocked"
        else:
            raise AssertionError("mismatching Workplace accepted")
        assert snapshot(core) == before
        # The immutable plan cannot authorize changed preimages.
        prepared = service.plan(args.candidate)
        (core / "LICENSE").write_bytes(b"drift after plan\n")
        try:
            native.replace_legacy_core(boundary, prepared)
        except native.NativeControlError:
            pass
        else:
            raise AssertionError("changed preimage accepted")
        (core / "LICENSE").write_bytes(b"local Core drift\n")
        assert not (core / "runtime/core-update/in-progress.json").exists()
        report["matrix"]["selection_and_preimage_refusals"] = "pass"
        assert update("apply")[0] == 1 and snapshot(core) == before
        if args.controlled_fault == "none":
            code, applied = update("apply", True)
        else:
            # Both faults are actual Windows share-lock failures. Finalization
            # fails after SQL readiness; no migration/authority mock is involved.
            victim = core / (
                "VERSION"
                if args.controlled_fault == "copy"
                else "runtime/core-update/last-apply.json"
            )
            victim.parent.mkdir(parents=True, exist_ok=True)
            if not victim.exists():
                victim.write_bytes(b"{}")
            kernel, handle = native._receipt_handle(victim, 0x80000000, 0)
            try:
                assert update("apply", True)[0] == 1
                journal = core / "runtime/core-update/in-progress.json"
                failed = journal.read_bytes()
                (out / "fault-journal.json").write_bytes(failed)
                if args.controlled_fault == "copy":
                    assert (core / native.MANIFEST).read_bytes() == release.manifest
                    assert not (project / ".pf/data/execution-storage.json").exists()
                    assert update("repair", True)[0] == 1
                    assert boundary.update_plan is not None
                    backup = (
                        Path(json.loads(journal.read_bytes())["backup_dir"])
                        / "files/LICENSE"
                    )
                    backup_preimage = backup.read_bytes()
                    backup.write_bytes(b"corrupt backup")
                    try:
                        assert update("repair", True)[0] == 1
                    finally:
                        backup.write_bytes(backup_preimage)
                    report["matrix"]["wrong_backup_refused"] = "pass"
                else:
                    assert boundary.update_children[-1].retired()
                    assert boundary.update_children[-1].response is not None
                    assert "_original_terminal" in boundary.update_children[-1].response
                wrong = control / "wrong.zip"
                wrong.write_bytes(args.candidate.read_bytes() + b"wrong")
                try:
                    assert boundary.update_plan is not None
                    service.resume(
                        wrong, update_id=boundary.update_plan.update_id, confirm=True
                    )
                except Exception as error:
                    assert getattr(error, "code", None) == "plan_blocked"
                else:
                    raise AssertionError("wrong archive accepted")
            finally:
                kernel.CloseHandle(handle)
            code, applied = update("repair", True)
            report["matrix"]["real_" + args.controlled_fault + "_forward_resume"] = (
                "pass"
            )
        assert code == 0 and original_update_succeeded(applied)
        assert boundary.update_children[-1].retired()
        report["fresh_child_pid"] = boundary.update_children[-1].process.pid
        assert report["fresh_child_pid"] != os.getpid()
        assert all((core / n).read_bytes() == raw for n, raw in sentinels.items())
        assert all((project / n).read_bytes() == raw for n, raw in history.items())
        assert all(
            sha256((root / n).read_bytes()) == value
            for n, value in identities_before.items()
        )
        stores_after = {
            str(t.target): store_identity(t) for t in storage_context.targets
        }
        assert all(identity is not None for identity in stores_after.values())
        assert all(
            stores_after[name] == identity
            for name, identity in stores_before.items()
            if identity is not None
        )
        report["store_ids"] = {
            str(Path(name).relative_to(root)): identity.store_id
            for name, identity in stores_after.items()
        }
        binding = json.loads((project / ".pf/data/execution-storage.json").read_bytes())
        database = project / ".pf" / binding["target_relative_path"]

        def state() -> Any:
            with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as sql:
                assert sql.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                return sql.execute(
                    "SELECT project_id,authority,readiness,active_coverage FROM execution_state WHERE singleton=1"
                ).fetchone()

        assert state() == (binding["project_id"], "sql", "ready", "complete")
        with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as sql:
            assert sql.execute(
                "SELECT outcome,collection FROM execution_attempts WHERE task_id=?",
                (old_work["assignment_id"],),
            ).fetchone() == ("completed", "collected")
        assert (
            old_output.read_text(encoding="utf-8") == "Controlled worker completed.\n"
        )
        report["binding"] = binding
        report["matrix"]["genuine_to_sql"] = "pass"
        for ingress, commands in routes.items():
            for argv in commands:
                try:
                    launch(argv, ingress)
                except native.NativeControlError:
                    pass
                else:
                    raise AssertionError("old ingress reopened after replacement")
        current = [executable, "-I", "-B", str(core / "bin/pf.py")]

        def new(
            label: str, options: list[str], body: bytes = b"", expected: int = 0
        ) -> bytes:
            process = native.spawn_owned(
                current + options,
                cwd=root,
                env=environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return collect(label, process, body, expected)

        selectors = ["--project-root", str(project), "--task", work["assignment_id"]]
        install_echo_driver(project, manager, executable)
        for action in ("prepare", "start", "status", "collect"):
            options = ["worker-run", action, *selectors]
            if action in {"prepare", "start"}:
                options += ["--driver", "controlled-echo"]
            if action == "start":
                options += ["--wait"]
            new("new-worker-" + action, options)
        assert (project / ".pf/artifacts/controlled/report.md").read_text(
            encoding="utf-8"
        ) == "Controlled worker completed.\n"
        assert (
            json.loads((project / ".pf/data/execution-storage.json").read_bytes())
            == binding
        )
        assert state() == (binding["project_id"], "sql", "ready", "complete")
        report["matrix"]["worker_lifecycle"] = "pass"
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "pf.work.state",
                    "arguments": {
                        "project_root": str(project),
                        "run_id": work["run_id"],
                        "assignment_id": work["assignment_id"],
                        "context_id": work["context"]["id"],
                    },
                },
            },
        ]
        process = native.spawn_owned(
            [
                executable,
                "-I",
                "-B",
                str(core / "tools/pf_runtime/mcp_server.py"),
                "--workplace",
                str(workplace),
                "--session",
                "controlled",
            ],
            cwd=root,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        responses = collect(
            "new-mcp", process, ("\n".join(map(json.dumps, requests)) + "\n").encode()
        )
        rows = [json.loads(line) for line in responses.splitlines()]
        assert len(rows) == 2 and "error" not in rows[1]
        assert rows[1]["result"].get("isError") is not True
        result = json.loads(rows[1]["result"]["content"][0]["text"])
        assert result["assignment"]["id"] == work["assignment_id"]
        assert result["context"]["checksum"] == work["context"]["checksum"]
        report["matrix"]["mcp_exact_work"] = "pass"
        # Real current entry must refuse foreign epochs and a substituted guard.
        # Restore the exact original object; no new generation is invented.
        store_ids = report["store_ids"].copy()
        epoch_path = core / "runtime/native-control/epoch"
        old_epoch = epoch_path.read_bytes()
        epoch_path.write_bytes(b"foreign-epoch")
        try:
            new("foreign-epoch-refused", ["version"], expected=1)
        finally:
            epoch_path.write_bytes(old_epoch)
        guard_path = core / "runtime/native-control/installation.guard"
        saved_guard = guard_path.with_name("fixture-original-guard")
        guard_path.rename(saved_guard)
        guard_path.write_bytes(saved_guard.read_bytes())
        try:
            new("substituted-guard-refused", ["version"], expected=1)
        finally:
            guard_path.unlink()
            saved_guard.rename(guard_path)
        new("restored-exact-native-objects", ["version"])
        assert {
            str(t.target.relative_to(root)): store_identity(t).store_id
            for t in storage_context.targets
        } == store_ids
        report["matrix"]["epoch_and_guard_substitution_refused"] = "pass"
        verify_runtime_closure()
        report["matrix"]["protected_runtime_closure_unchanged"] = "pass"
        report["status"] = "passed"
        save()
        return 0
    finally:
        save()
        for owners in boundary.owners.values():
            for process in owners:
                job = getattr(process, "native_job")
                if job.active():
                    job.stop(deadline=time.monotonic() + 10)
                process.wait(timeout=10)
                job.close()
        for number, attempt in enumerate(boundary.update_children, 1):
            for stream in ("stdout", "stderr"):
                content = getattr(attempt, stream)
                if content is not None:
                    (
                        out / ("fresh-child-" + str(number) + "." + stream + ".log")
                    ).write_bytes(content)
            job = getattr(attempt.process, "native_job")
            if job.active():
                job.stop(deadline=time.monotonic() + 10)
            attempt.process.wait(timeout=10)
            job.close()
        boundary.anchor.close()


if __name__ == "__main__":
    if sys.argv[1:] != ["--runtime-probe"]:
        raise SystemExit(2)
    require_disposable_ci()
    raise SystemExit(runtime_probe())
