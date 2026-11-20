"""Regression tests for non-mutating context reads and explicit writer workflows."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

import yaml

TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

# These tests exercise the bundled source entrypoint after adding its tools root.
import processforge as pf  # noqa: E402
from specialization_smoke_helpers import (  # noqa: E402
    write_process_with_capability,
    write_project,
    write_specialization,
    write_workspace,
)


class ContextResolveSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_parent = Path(tempfile.gettempdir()).resolve()
        self.temporary = self.temp_parent / f"pf-context-safety-{uuid.uuid4().hex}"
        self.temporary.mkdir()
        self.addCleanup(self.remove_fixture)
        self.root = self.temporary / "project with spaces"
        self.flow = self.root / ".pf"
        self.flow.mkdir(parents=True)
        (self.flow / "process-forge.yaml").write_text(
            "schema_version: 1\nproject:\n  id: fixture\n"
            "process_forge:\n  mode: file_only\n",
            encoding="utf-8",
        )
        (self.flow / "AGENTS.md").write_text("# Fixture\n", encoding="utf-8")
        self.snapshot = self.flow / "contexts/project-context.snapshot.yaml"

    def remove_fixture(self) -> None:
        selected = self.temporary.resolve()
        self.assertEqual(self.temp_parent, selected.parent)
        shutil.rmtree(selected)

    def seed_legacy_files(self) -> None:
        for relative in (
            "contexts/context-index.yaml",
            "contexts/resolved-rules.yaml",
            "contexts/context-conflict-report.md",
            "runtime/cache/context-cache.yaml",
        ):
            path = self.flow / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("sentinel: preserve\n", encoding="utf-8")
            os.utime(path, ns=(1_700_000_000_000_000_000,) * 2)

    def inventory(self, flow: Path | None = None) -> dict:
        selected = flow or self.flow
        return {
            path.relative_to(selected).as_posix(): (
                path.read_bytes(),
                path.stat().st_mtime_ns,
            )
            for directory in (selected / "contexts", selected / "runtime/cache")
            for path in directory.rglob("*")
            if path.is_file()
        }

    def fresh_snapshot(self) -> dict:
        _, paths, snapshot, _ = pf.write_project_context_snapshot_outputs(self.root)
        self.assertTrue(all(path.is_relative_to(self.root) for path in paths.values()))
        self.assertEqual("fresh", pf.project_context_check_result(self.root)["status"])
        return snapshot

    def invoke(self, *options: str, root: Path | None = None) -> tuple[int, str]:
        args = pf.build_parser().parse_args(
            ["context-resolve", "--project-root", str(root or self.root), *options]
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = args.func(args)
        return code, output.getvalue()

    def read_json(self, *options: str, root: Path | None = None) -> tuple[int, dict]:
        code, output = self.invoke(*options, "--json", root=root)
        return code, json.loads(output)

    def test_default_json_reads_canonical_snapshot_and_preserves_unknown_fields(
        self,
    ) -> None:
        self.seed_legacy_files()
        snapshot = self.fresh_snapshot()
        snapshot["legacy_extension"] = {"unrecognized": ["keep", "значение"]}
        self.snapshot.write_text(pf.dump_yaml(snapshot), encoding="utf-8")
        before = self.inventory()
        code, payload = self.read_json()
        self.assertEqual(0, code)
        self.assertEqual(snapshot, payload["snapshot"])
        self.assertEqual("fresh", payload["check"]["status"])
        self.assertEqual("continue", payload["check"]["policy_action"])
        self.assertEqual(before, self.inventory())

    def test_default_yaml_is_structured_and_does_not_write(self) -> None:
        snapshot = self.fresh_snapshot()
        before = self.inventory()
        code, output = self.invoke()
        payload = yaml.safe_load(output)
        self.assertEqual(0, code)
        self.assertEqual(snapshot, payload["snapshot"])
        self.assertEqual("fresh", payload["check"]["status"])
        self.assertEqual(before, self.inventory())

    def test_missing_snapshot_returns_json_error_without_creating_context(self) -> None:
        before = self.inventory()
        code, payload = self.read_json()
        self.assertEqual(1, code)
        self.assertEqual({}, payload["snapshot"])
        self.assertTrue(payload["check"]["broken"])
        self.assertEqual(
            "project-context-refresh", payload["check"]["recommended_action"]
        )
        self.assertEqual(before, self.inventory())
        self.assertFalse((self.flow / "contexts").exists())
        self.assertFalse((self.flow / "runtime/cache").exists())

    def test_missing_snapshot_does_not_overwrite_legacy_sentinels(self) -> None:
        self.seed_legacy_files()
        before = self.inventory()
        code, payload = self.read_json()
        self.assertEqual(1, code)
        self.assertTrue(payload["check"]["broken"])
        self.assertEqual(before, self.inventory())

    def test_broken_snapshot_is_not_repaired(self) -> None:
        self.seed_legacy_files()
        for text in ("snapshot: [unterminated\n", "schema_version: 1\n", "[]\n"):
            with self.subTest(snapshot=text):
                self.snapshot.write_text(text, encoding="utf-8")
                before = self.inventory()
                code, payload = self.read_json()
                self.assertEqual(1, code)
                self.assertEqual({}, payload["snapshot"])
                self.assertEqual("broken", payload["check"]["status"])
                self.assertEqual(before, self.inventory())

    def test_stale_context_preserves_policy_and_never_refreshes(self) -> None:
        snapshot = self.fresh_snapshot()
        snapshot["snapshot"]["valid_until"] = "2000-01-01T00:00:00Z"
        for action, expected_code in (("ask_operator", 0), ("block", 1)):
            with self.subTest(action=action):
                snapshot["context_policy"]["on_session_start"]["if_stale"] = action
                self.snapshot.write_text(pf.dump_yaml(snapshot), encoding="utf-8")
                before = self.inventory()
                code, payload = self.read_json()
                self.assertEqual(expected_code, code)
                self.assertEqual("stale", payload["check"]["status"])
                self.assertEqual(action, payload["check"]["policy_action"])
                self.assertEqual(snapshot, payload["snapshot"])
                self.assertEqual(before, self.inventory())

    def test_subsequent_read_observes_same_size_same_mtime_change(self) -> None:
        snapshot = self.fresh_snapshot()
        snapshot["legacy_extension"] = "alpha"
        self.snapshot.write_text(pf.dump_yaml(snapshot), encoding="utf-8")
        _, first = self.read_json()
        stat = self.snapshot.stat()
        original = self.snapshot.read_bytes()
        changed = original.replace(b"alpha", b"bravo")
        self.assertNotEqual(original, changed)
        self.assertEqual(len(original), len(changed))
        self.snapshot.write_bytes(changed)
        os.utime(self.snapshot, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        before = self.inventory()
        _, second = self.read_json()
        self.assertEqual("alpha", first["snapshot"]["legacy_extension"])
        self.assertEqual("bravo", second["snapshot"]["legacy_extension"])
        self.assertEqual(before, self.inventory())

    def test_workplace_only_keeps_default_branch_and_forwards_override(self) -> None:
        self.fresh_snapshot()
        workplace = write_workspace(self.temporary)
        before = self.inventory()
        _, payload = self.read_json("--workplace", str(workplace))
        self.assertIn("snapshot", payload)
        self.assertNotIn("resolved_context", payload)
        expected = pf.project_context_check_result(
            self.root, explicit_workplace=str(workplace)
        )
        self.assertEqual(expected, payload["check"])
        self.assertEqual(before, self.inventory())

    def test_explicit_selector_branches_keep_payload_and_exit_codes(self) -> None:
        workplace = write_workspace(self.temporary)
        write_specialization(
            workplace, "fixture.specialization.dev", tool="fixture.tool.a"
        )
        project = write_project(self.temporary, workplace)
        write_process_with_capability(project, capability="fixture.capability.tool-a")
        cases = (
            ("--platform", "fixture.platform.child"),
            ("--process", "fixture-process-a"),
            ("--specialization", "fixture.specialization.dev"),
            (
                "--platform",
                "fixture.platform.child",
                "--specialization",
                "fixture.specialization.dev",
            ),
        )
        for selector in cases:
            with self.subTest(selector=selector):
                flow = project / ".pf"
                before = self.inventory(flow)
                code, payload = self.read_json(
                    *selector, "--workplace", str(workplace), root=project
                )
                self.assertEqual({"resolved_context"}, set(payload))
                resolved = payload["resolved_context"]
                self.assertEqual(1 if resolved["conflicts"] else 0, code)
                self.assertIn("activated_tools", resolved)
                if "--platform" in selector and "--specialization" in selector:
                    self.assertIn("fixture.tool.a", resolved["activated_tools"])
                if selector[0] == "--process":
                    self.assertEqual("fixture-process-a", resolved["process"])
                self.assertEqual(before, self.inventory(flow))

    def test_selector_conflict_stays_json_and_does_not_write(self) -> None:
        before = self.inventory()
        code, payload = self.read_json("--specialization", "fixture.missing")
        self.assertEqual(1, code)
        self.assertTrue(payload["resolved_context"]["conflicts"])
        self.assertEqual(before, self.inventory())

    def test_cli_json_is_one_document_for_path_with_spaces(self) -> None:
        self.fresh_snapshot()
        self.seed_legacy_files()
        before = self.inventory()
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(TOOLS / "processforge.py"),
                "context-resolve",
                "--project-root",
                str(self.root),
                "--json",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONIOENCODING": "utf-8",
            },
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("fresh", json.loads(result.stdout)["check"]["status"])
        self.assertNotIn("DEPRECATED", result.stdout)
        self.assertNotIn("WROTE:", result.stdout)
        self.assertEqual(before, self.inventory())

    def test_missing_project_and_flow_keep_existing_guards(self) -> None:
        for root, message in (
            (self.root / "missing", "project root not found"),
            (self.temporary, "FAIL:"),
        ):
            with self.subTest(root=root), self.assertRaises(SystemExit) as caught:
                self.invoke("--json", root=root)
            if "missing" in str(root):
                self.assertIn(message, str(caught.exception))
            else:
                self.assertIn("FAIL:", str(caught.exception))

    def test_explicit_snapshot_writer_still_creates_generation_and_preserves_capsule(
        self,
    ) -> None:
        capsule = self.flow / "contexts/assignment-capsules/fixture.capsule.yaml"
        capsule.parent.mkdir(parents=True)
        capsule.write_text("immutable: keep\n", encoding="utf-8")
        before = (capsule.read_bytes(), capsule.stat().st_mtime_ns)
        snapshot = self.fresh_snapshot()
        self.assertTrue(self.snapshot.is_file())
        self.assertEqual(before, (capsule.read_bytes(), capsule.stat().st_mtime_ns))
        self.assertTrue(
            any(
                path.name == f"{snapshot['snapshot']['id']}.yaml"
                for path in (self.flow / "contexts").rglob("*.yaml")
            )
        )

    def test_explicit_legacy_writer_still_writes_four_outputs(self) -> None:
        status, paths = pf.write_context_outputs(self.root)
        self.assertNotEqual("blocked", status)
        self.assertEqual(4, len(paths))
        self.assertTrue(all(path.is_file() for path in paths.values()))

    def test_explicit_compile_still_writes_and_refuses_existing_ecp(self) -> None:
        assignment = self.root / "fixture-assignment.md"
        assignment.write_text("# Fixture assignment\n", encoding="utf-8")
        pf.write_context_outputs(self.root)
        args = pf.build_parser().parse_args(
            [
                "context-compile",
                "--project-root",
                str(self.root),
                "--assignment",
                str(assignment),
                "--capsule",
            ]
        )
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, args.func(args))
        ecp = self.flow / "contexts/fixture-assignment.ecp.yaml"
        capsule = self.flow / "contexts/fixture-assignment.capsule.yaml"
        before = (ecp.read_bytes(), capsule.read_bytes())
        with (
            contextlib.redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit) as caught,
        ):
            args.func(args)
        self.assertIn("ECP already exists", str(caught.exception))
        self.assertEqual(before, (ecp.read_bytes(), capsule.read_bytes()))


if __name__ == "__main__":
    unittest.main()
