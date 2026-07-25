#!/usr/bin/env python3
"""Smoke checks for ProcessForge Resource Management MVP commands."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("PF_REPO_ROOT", Path(__file__).resolve().parents[4])).resolve()
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command

CLI = ROOT / "tools" / "processforge.py"
DEFAULT_TIMEOUT = 60


def run_cmd(command: list[str], cwd: Path = ROOT, timeout: int = DEFAULT_TIMEOUT, expect: int = 0) -> CommandResult:
    result = run_processforge_command(command, cwd=cwd, timeout=timeout)
    if result.timed_out:
        print("FAIL smoke_resource_management: timeout")
        print(diagnostic_text(result))
        raise AssertionError(f"timeout after {timeout}s: {' '.join(command)}")
    if result.returncode != expect:
        print("FAIL smoke_resource_management: unexpected command exit")
        print("Expected exit code:")
        print(f"  {expect}")
        print(diagnostic_text(result))
        raise AssertionError(f"expected exit {expect}, got {result.returncode}: {' '.join(command)}")
    return result


def run(*args: str, expect: int = 0) -> CommandResult:
    return run_cmd([sys.executable, str(CLI), *args], expect=expect)


def command_output(result: CommandResult) -> str:
    return result.stdout + result.stderr


def run_test(name: str, func: object) -> None:
    print(f"RUN: {name}")
    try:
        func()
    except Exception as exc:
        print(f"FAIL smoke_resource_management: {name}")
        raise
    print(f"PASS: {name}")


def run_public_cleanliness() -> None:
    run_cmd(
        [sys.executable, str(ROOT / "tools" / "validate-public-cleanliness.py"), "--root", str(ROOT)],
        cwd=ROOT,
        timeout=60,
    )


def assert_exists(path: Path) -> None:
    if not path.exists():
        raise AssertionError(f"missing expected path: {path}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-rm-smoke-") as tmp:
        workplace = Path(tmp) / "workplace"
        workplace.mkdir()
        (workplace / "knowledge" / "example" / "docs").mkdir(parents=True)
        package_root = workplace / "knowledge" / "packages"
        package_root.mkdir(parents=True)
        alt_package_root = workplace / "knowledge" / "alt-packages"
        alt_package_root.mkdir(parents=True)
        (workplace / "reusable-templates" / "file").mkdir(parents=True)
        (workplace / "tools").mkdir()
        (workplace / "mcp").mkdir()
        (workplace / "cache").mkdir()
        (workplace / "runtime").mkdir()
        (workplace / "logs").mkdir()
        (workplace / "registries").mkdir()
        (workplace / "workplace.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "workplace:",
                    "  id: smoke-workplace",
                    "  name: Smoke Workplace",
                    "  type: workstation",
                    "  os: windows",
                    "paths:",
                    "  root: .",
                    "  registries: registries",
                    "  cache: cache",
                    "  runtime: runtime",
                    "  logs: logs",
                    "path_constants:",
                    "  PF_WORKPLACE: .",
                    "  PF_KNOWLEDGE: knowledge",
                    "  PF_TEMPLATES: reusable-templates",
                    "  PF_TOOLS: tools",
                    "  PF_MCP: mcp",
                    "registries:",
                    "  distributions: registries/distributions.yaml",
                    "  platforms: registries/platforms.yaml",
                    "  knowledge_roots: registries/knowledge-roots.yaml",
                    "  package_roots: registries/package-roots.yaml",
                    "  templates: registries/templates.yaml",
                    "  tools: registries/tools.yaml",
                    "  mcp: registries/mcp.yaml",
                    "policies:",
                    "  do_not_store_secret_values: true",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (workplace / "registries" / "distributions.yaml").write_text("schema_version: 1\ndistributions: []\n", encoding="utf-8")
        (workplace / "registries" / "platforms.yaml").write_text("schema_version: 1\nplatforms: []\n", encoding="utf-8")
        (workplace / "registries" / "package-roots.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "package_roots:",
                    "  - id: global",
                    "    label: Global packages",
                    "    path: ${PF_KNOWLEDGE}/packages",
                    "    scope: workplace",
                    "    status: available",
                    "    writable: true",
                    "    default: true",
                    "  - id: alternate",
                    "    label: Alternate packages",
                    "    path: ${PF_KNOWLEDGE}/alt-packages",
                    "    scope: workplace",
                    "    status: available",
                    "    writable: true",
                    "  - id: missing-root",
                    "    label: Missing packages",
                    "    path: ${PF_KNOWLEDGE}/missing-packages",
                    "    scope: workplace",
                    "    status: optional",
                    "    writable: true",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        windows_abs = "D" + ":/" + "Knowledge/Example"
        posix_abs = "/" + "srv" + "/knowledge/example"
        (workplace / "registries" / "knowledge-roots.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "knowledge_roots:",
                    "  - id: example-root",
                    "    label: Example Root",
                    "    path: ${PF_KNOWLEDGE}/example",
                    "    scope: workplace",
                    "    visibility: private",
                    "    indexing_policy: manual",
                    "  - id: external-windows",
                    "    label: External Windows",
                    f"    path: {windows_abs}",
                    "    scope: workplace",
                    "    visibility: private",
                    "    indexing_policy: manual",
                    "    status: optional",
                    "  - id: external-posix",
                    "    label: External POSIX",
                    f"    path: {posix_abs}",
                    "    scope: workplace",
                    "    visibility: private",
                    "    indexing_policy: manual",
                    "    status: optional",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (workplace / "registries" / "templates.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "template_roots:",
                    "  - id: file-templates",
                    "    label: File Templates",
                    "    path: ${PF_TEMPLATES}/file",
                    "    scope: workplace",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (workplace / "registries" / "tools.yaml").write_text("schema_version: 1\ntools: []\n", encoding="utf-8")
        (workplace / "registries" / "mcp.yaml").write_text("schema_version: 1\nmcp_servers: []\n", encoding="utf-8")

        resolved = run("path-resolve", "--workplace", str(workplace), "--path", "${PF_KNOWLEDGE}/example/docs")
        if "resolved_from_constant" not in command_output(resolved):
            raise AssertionError("path-resolve did not expand PF_KNOWLEDGE")
        run("doctor-workplace", "--root", str(workplace))

        run(
            "knowledge-add-url",
            "--workplace",
            str(workplace),
            "--package",
            "platform.example",
            "--package-root",
            "global",
            "--url",
            "https://example.com/example/article",
            "--kind",
            "article",
        )
        proposals = list((workplace / "runtime" / "resource-management" / "proposals").glob("*knowledge-add-url*.yaml"))
        if not proposals:
            raise AssertionError("knowledge-add-url dry-run did not create a proposal")
        proposal_text = proposals[-1].read_text(encoding="utf-8")
        if "package_root: global" not in proposal_text:
            raise AssertionError("knowledge-add-url dry-run proposal did not record selected package root")

        run(
            "knowledge-add-url",
            "--workplace",
            str(workplace),
            "--package",
            "platform.example",
            "--package-root",
            "global",
            "--url",
            "https://example.com/example/applied",
            "--kind",
            "article",
            "--apply",
        )

        resource_file = Path(tmp) / "resource.yaml"
        resource_file.write_text(
            "\n".join(
                [
                    "id: example-source",
                    "kind: source_tree",
                    "title: Example source mirror",
                    f"path: {str((workplace / 'knowledge' / 'example' / 'docs').as_posix())}",
                    "load_policy: on_demand",
                    "index_policy: symbols",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        run(
            "knowledge-add-resource",
            "--workplace",
            str(workplace),
            "--package",
            "platform.example",
            "--package-root",
            "global",
            "--resource-file",
            str(resource_file),
            "--apply",
        )
        package_manifest = package_root / "platform.example" / "package.yaml"
        resource_index = package_root / "platform.example" / "indexes" / "resource-index.yaml"
        assert_exists(package_manifest)
        assert_exists(resource_index)
        if (workplace / "packages" / "platform.example" / "package.yaml").exists():
            raise AssertionError("package was written to legacy workplace/packages despite package_roots registry")
        package_text = package_manifest.read_text(encoding="utf-8")
        if "registry: knowledge_roots" not in package_text or "id: example-root" not in package_text:
            raise AssertionError("absolute resource path under known root did not become knowledge_roots path_ref")
        if "package_root: global" not in package_text:
            raise AssertionError("package manifest did not record authoritative package_root")
        if str((workplace / "knowledge").as_posix()) in package_text:
            raise AssertionError("package manifest retained resolved absolute resource path")
        index_text = resource_index.read_text(encoding="utf-8")
        if "package_root: global" not in index_text:
            raise AssertionError("resource index did not record selected package_root")

        run("knowledge-index-refresh", "--workplace", str(workplace), "--package", "platform.example", "--package-root", "global", "--apply")
        run("knowledge-package-doctor", "--workplace", str(workplace), "--package", "platform.example", "--package-root", "global")
        unknown_root = run(
            "knowledge-add-resource",
            "--workplace",
            str(workplace),
            "--package",
            "platform.example",
            "--package-root",
            "unknown-root",
            "--resource-file",
            str(resource_file),
            "--apply",
            expect=1,
        )
        if "package root 'unknown-root' not found" not in command_output(unknown_root):
            raise AssertionError("unknown package root id did not fail")
        missing_root = run(
            "knowledge-add-resource",
            "--workplace",
            str(workplace),
            "--package",
            "platform.example",
            "--package-root",
            "missing-root",
            "--resource-file",
            str(resource_file),
            "--apply",
            expect=1,
        )
        if "path does not exist" not in command_output(missing_root):
            raise AssertionError("missing selected package root path did not fail on apply")

        template_source = Path(tmp) / "template-source"
        template_source.mkdir()
        (template_source / "README.md").write_text("# Template\n", encoding="utf-8")
        run("template-add", "--workplace", str(workplace), "--type", "file", "--id", "example-file-template", "--source", str(template_source))
        run("tool-register", "--workplace", str(workplace), "--id", "phpstan", "--capability", "php.static_analysis", "--command", "phpstan")
        run("mcp-register", "--workplace", str(workplace), "--id", "context7", "--capability", "official_documentation", "--command", "context7")

        missing_pkg = package_root / "missing-ref" / "package.yaml"
        missing_pkg.parent.mkdir(parents=True)
        missing_pkg.write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "id: missing-ref",
                    "name: Missing Ref",
                    "version: 0.1.0",
                    "kind: platform",
                    "scope: workplace",
                    "resources:",
                    "  - id: missing-docs",
                    "    kind: documentation",
                    "    title: Missing docs",
                    "    path_ref:",
                    "      registry: knowledge_roots",
                    "      id: missing-docs",
                    "    load_policy: on_demand",
                    "    index_policy: full_text",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        failed = run("knowledge-package-doctor", "--workplace", str(workplace), "--package", "missing-ref", expect=1)
        if "FAIL" not in command_output(failed):
            raise AssertionError("knowledge-package-doctor did not fail on missing path_ref target")

        heavy_pkg = package_root / "heavy-warning" / "package.yaml"
        heavy_pkg.parent.mkdir(parents=True)
        heavy_pkg.write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "id: heavy-warning",
                    "name: Heavy Warning",
                    "version: 0.1.0",
                    "kind: platform",
                    "scope: workplace",
                    "resources:",
                    "  - id: heavy-source",
                    "    kind: source_tree",
                    "    title: Heavy source",
                    "    path_ref:",
                    "      registry: external_resources",
                    "      id: heavy-source",
                    "    index_policy: symbols",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        warned = run("knowledge-package-doctor", "--workplace", str(workplace), "--package", "heavy-warning")
        if "WARN" not in command_output(warned):
            raise AssertionError("knowledge-package-doctor did not warn on heavy resource without load_policy")

        duplicate_pkg = alt_package_root / "platform.example" / "package.yaml"
        duplicate_pkg.parent.mkdir(parents=True)
        duplicate_pkg.write_text(package_text, encoding="utf-8")
        duplicate_doctor = run("knowledge-package-doctor", "--workplace", str(workplace), "--package", "platform.example")
        if "duplicate package id" not in command_output(duplicate_doctor):
            raise AssertionError("knowledge-package-doctor did not warn on duplicate package id across roots")
        duplicate_write = run(
            "knowledge-add-resource",
            "--workplace",
            str(workplace),
            "--package",
            "platform.example",
            "--resource-file",
            str(resource_file),
            "--apply",
            expect=1,
        )
        duplicate_write_output = command_output(duplicate_write)
        if "duplicate package id" not in duplicate_write_output or "--package-root" not in duplicate_write_output:
            raise AssertionError("write without --package-root did not fail on duplicate package id")

        bad_workplace = Path(tmp) / "bad-workplace"
        bad_workplace.mkdir()
        (bad_workplace / "registries").mkdir()
        (bad_workplace / "workplace.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "workplace:",
                    "  id: bad-workplace",
                    "  name: Bad Workplace",
                    "  type: workstation",
                    "  os: windows",
                    "paths:",
                    "  root: .",
                    "path_constants:",
                    "  PF_WORKPLACE: .",
                    "registries:",
                    "  knowledge_roots: ${PF_UNKNOWN}/knowledge-roots.yaml",
                    "policies: {}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        unknown = run("doctor-workplace", "--root", str(bad_workplace), expect=1)
        if "unknown path constant" not in command_output(unknown):
            raise AssertionError("doctor-workplace did not fail on unknown path constant")

        project = Path(tmp) / "project"
        (project / ".pf" / "contexts").mkdir(parents=True)
        (project / ".pf" / "runtime").mkdir(parents=True)
        (project / ".pf" / "process-forge.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "project:",
                    "  id: smoke",
                    "  name: Smoke",
                    "workplace:",
                    "  reference: auto",
                    "paths: {}",
                    "policies: {}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (project / ".pf" / "hooks.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "hooks:",
                    "  mode: outbox",
                    "  default_timeout: 0",
                    "  network_send_enabled: false",
                    "  targets: []",
                    "policies:",
                    "  do_not_send_network_by_default: true",
                    "  secrets_are_refs_only: true",
                    "  chat_content_requires_opt_in: true",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (project / ".gitignore").write_text(".pf/process-forge.local.yaml\n.pf/runtime/\n.pf/cache/\n", encoding="utf-8")
        private_leak = "D" + ":/" + "Private/Knowledge"
        (project / ".pf" / "contexts" / "project-context.snapshot.yaml").write_text(f"schema_version: 1\nleak: {private_leak}\n", encoding="utf-8")
        (project / ".pf" / "contexts" / "project-context.snapshot.md").write_text(private_leak + "\n", encoding="utf-8")
        leaked = run("doctor-project", "--project-root", str(project), expect=1)
        if "contains no local absolute paths" not in command_output(leaked):
            raise AssertionError("doctor-project did not fail on absolute path in public snapshot")

    run_public_cleanliness()
    print("PASS: resource management smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
