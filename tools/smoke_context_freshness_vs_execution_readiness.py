"""Smoke test for separating context freshness from execution readiness."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "processforge.py"), *args],
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout


def mcp_call(workplace: Path, session: str, requests: list[dict]) -> list[dict]:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "pf_runtime" / "mcp_server.py"),
            "--workplace",
            str(workplace),
            "--session",
            session,
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        input="\n".join(json.dumps(item) for item in requests) + "\n",
        capture_output=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-readiness-smoke-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        project = root / "project"
        docs_dir = root / "fixture-docs"
        project.mkdir()
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text(
            "Platform resource search proof for execution readiness separation.",
            encoding="utf-8",
        )

        run_cli("workplace-init", "--workplace", str(workplace), "--apply")
        run_cli(
            "knowledge-package-create",
            "--workplace",
            str(workplace),
            "--id",
            "docs.example-domain",
            "--title",
            "Platform Fixture Docs",
            "--package-root",
            "global",
            "--kind",
            "documentation",
            "--apply",
        )
        resource_file = root / "joomla-resource.yaml"
        resource_file.write_text(
            yaml.safe_dump(
                {
                    "id": "example-domain",
                    "kind": "documentation",
                    "title": "Platform Fixture Resource",
                    "path": str(docs_dir),
                    "index_policy": "full_text",
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        run_cli(
            "knowledge-add-resource",
            "--workplace",
            str(workplace),
            "--package",
            "docs.example-domain",
            "--resource-file",
            str(resource_file),
            "--apply",
        )
        run_cli(
            "project-onboard",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--type",
            "generic",
            "--apply",
        )

        for registry_name, collection in [("tools.yaml", "tools"), ("mcp.yaml", "mcp_servers")]:
            registry = project / ".pf" / "registries" / registry_name
            if registry.is_file():
                data = yaml.safe_load(registry.read_text(encoding="utf-8")) or {}
                data[collection] = []
                registry.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

        manifest_path = project / ".pf" / "process-forge.yaml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest["required_capabilities"] = ["filesystem.write"]
        manifest.setdefault("knowledge_stack", []).append(
            {"id": "docs.example-domain", "version": "*", "source": "workplace"}
        )
        manifest.setdefault("context_requirements", {}).setdefault("knowledge_packages", []).append(
            {"id": "docs.example-domain", "constraint": "*", "required": True}
        )
        manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")

        run_cli(
            "project-context-refresh",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--apply",
        )
        check = json.loads(
            run_cli(
                "project-context-check",
                "--project-root",
                str(project),
                "--workplace",
                str(workplace),
                "--json",
            )
        )
        assert check["status"] == "fresh", check
        assert check["execution_readiness"]["status"] == "blocked", check
        assert check["execution_readiness"]["missing_capabilities"][0]["capability"] == "filesystem.write", check

        run_cli("search-index", "refresh", "--project-root", str(project), "--workplace", str(workplace))
        run_cli(
            "agent-checkin",
            "--workplace",
            str(workplace),
            "--agent",
            "readiness-smoke",
            "--session",
            "readiness-session",
            "--project-root",
            str(project),
            "--role",
            "verifier",
        )
        responses = mcp_call(
            workplace,
            "readiness-session",
            [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "pf.session_context", "arguments": {"session_id": "readiness-session"}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "pf.search",
                        "arguments": {"session_id": "readiness-session", "query": "example-domain", "limit": 5},
                    },
                },
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "pf.resolve",
                        "arguments": {"session_id": "readiness-session", "resource_id": "docs.example-domain:example-domain"},
                    },
                },
            ],
        )
        session_context = json.loads(responses[1]["result"]["content"][0]["text"])
        assert session_context["context_freshness"]["status"] == "fresh", session_context
        assert session_context["execution_readiness"]["status"] == "blocked", session_context
        assert session_context["missing_capabilities"][0]["capability"] == "filesystem.write", session_context
        search_result = json.loads(responses[2]["result"]["content"][0]["text"])
        assert search_result["search_status"] == "fresh", search_result
        assert search_result["results"], search_result
        resolve_result = json.loads(responses[3]["result"]["content"][0]["text"])
        assert resolve_result["resource"]["status"] == "available", resolve_result

        run_cli(
            "project-context-mark-stale",
            "--project-root",
            str(project),
            "--subject",
            "docs.example-domain:example-domain",
            "--reason",
            "negative resolve gate",
        )
        stale_responses = mcp_call(
            workplace,
            "readiness-session",
            [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "pf.resolve",
                        "arguments": {"session_id": "readiness-session", "resource_id": "docs.example-domain:example-domain"},
                    },
                },
            ],
        )
        assert stale_responses[1]["result"].get("isError") is True, stale_responses
        stale_error = json.loads(stale_responses[1]["result"]["content"][0]["text"])
        assert stale_error["error"]["code"] == "snapshot_not_fresh", stale_error

        run_cli(
            "tool-register",
            "--workplace",
            str(workplace),
            "--id",
            "example-writer",
            "--name",
            "Example Writer",
            "--capability",
            "filesystem.write",
            "--command",
            "echo write",
            "--apply",
        )
        run_cli(
            "project-context-refresh",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--apply",
        )
        provider_check = json.loads(
            run_cli(
                "project-context-check",
                "--project-root",
                str(project),
                "--workplace",
                str(workplace),
                "--json",
            )
        )
        assert provider_check["execution_readiness"]["status"] == "ready", provider_check
        refreshed_snapshot = yaml.safe_load((project / ".pf" / "contexts" / "project-context.snapshot.yaml").read_text(encoding="utf-8"))
        assert refreshed_snapshot["capabilities"]["required"][0]["provider"] == "workplace:example-writer", refreshed_snapshot["capabilities"]

    print("PASS: context freshness is separate from execution readiness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
