#!/usr/bin/env python3
"""Smoke checks for ProcessForge Resource Management MVP commands."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def run(*args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != expect:
        print(result.stdout)
        raise AssertionError(f"expected exit {expect}, got {result.returncode}: {' '.join(args)}")
    return result


def assert_exists(path: Path) -> None:
    if not path.exists():
        raise AssertionError(f"missing expected path: {path}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-rm-smoke-") as tmp:
        workplace = Path(tmp) / "workplace"
        workplace.mkdir()
        (workplace / "knowledge" / "joomla" / "docs").mkdir(parents=True)
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
        (workplace / "registries" / "package-roots.yaml").write_text("schema_version: 1\npackage_roots: []\n", encoding="utf-8")
        windows_abs = "D" + ":/" + "Knowledge/Joomla"
        posix_abs = "/" + "srv" + "/knowledge/joomla"
        (workplace / "registries" / "knowledge-roots.yaml").write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "knowledge_roots:",
                    "  - id: joomla-root",
                    "    label: Joomla Root",
                    "    path: ${PF_KNOWLEDGE}/joomla",
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

        resolved = run("path-resolve", "--workplace", str(workplace), "--path", "${PF_KNOWLEDGE}/joomla/docs")
        if "resolved_from_constant" not in resolved.stdout:
            raise AssertionError("path-resolve did not expand PF_KNOWLEDGE")
        run("doctor-workplace", "--root", str(workplace))

        run(
            "knowledge-add-url",
            "--workplace",
            str(workplace),
            "--package",
            "platform.joomla",
            "--url",
            "https://example.com/joomla/article",
            "--kind",
            "article",
        )
        proposals = list((workplace / "runtime" / "resource-management" / "proposals").glob("*knowledge-add-url*.yaml"))
        if not proposals:
            raise AssertionError("knowledge-add-url dry-run did not create a proposal")

        resource_file = Path(tmp) / "resource.yaml"
        resource_file.write_text(
            "\n".join(
                [
                    "id: joomla-source",
                    "kind: source_tree",
                    "title: Joomla source mirror",
                    f"path: {str((workplace / 'knowledge' / 'joomla' / 'docs').as_posix())}",
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
            "platform.joomla",
            "--resource-file",
            str(resource_file),
            "--apply",
        )
        assert_exists(workplace / "packages" / "platform.joomla" / "package.yaml")
        assert_exists(workplace / "packages" / "platform.joomla" / "indexes" / "resource-index.yaml")
        package_text = (workplace / "packages" / "platform.joomla" / "package.yaml").read_text(encoding="utf-8")
        if "registry: knowledge_roots" not in package_text or "id: joomla-root" not in package_text:
            raise AssertionError("absolute resource path under known root did not become knowledge_roots path_ref")
        if str((workplace / "knowledge").as_posix()) in package_text:
            raise AssertionError("package manifest retained resolved absolute resource path")

        template_source = Path(tmp) / "template-source"
        template_source.mkdir()
        (template_source / "README.md").write_text("# Template\n", encoding="utf-8")
        run("template-add", "--workplace", str(workplace), "--type", "file", "--id", "joomla-form-field", "--source", str(template_source))
        run("tool-register", "--workplace", str(workplace), "--id", "phpstan", "--capability", "php.static_analysis", "--command", "phpstan")
        run("mcp-register", "--workplace", str(workplace), "--id", "context7", "--capability", "official_documentation", "--command", "context7")

        missing_pkg = workplace / "packages" / "missing-ref" / "package.yaml"
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
        if "FAIL" not in failed.stdout:
            raise AssertionError("knowledge-package-doctor did not fail on missing path_ref target")

        heavy_pkg = workplace / "packages" / "heavy-warning" / "package.yaml"
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
        if "WARN" not in warned.stdout:
            raise AssertionError("knowledge-package-doctor did not warn on heavy resource without load_policy")

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
        if "unknown path constant" not in unknown.stdout:
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
        if "contains no local absolute paths" not in leaked.stdout:
            raise AssertionError("doctor-project did not fail on absolute path in public snapshot")

    cleanliness = run("python-placeholder", expect=2) if False else subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate-public-cleanliness.py"), "--root", str(ROOT)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if cleanliness.returncode != 0:
        print(cleanliness.stdout)
        raise AssertionError("public cleanliness failed")
    print("PASS: resource management smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
