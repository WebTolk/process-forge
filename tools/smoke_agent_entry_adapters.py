"""Bounded source/transaction probes; no native client or model acceptance."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from processforge_core.agent_entry.contract import BOM, EntryError, digest, encoded, load_contract
from processforge_core.agent_entry.adapters import adapter_guide, apply_adapter, plan_adapter
from processforge_core.agent_entry.migration import manifest, pending, rollback_entry
from processforge_core.agent_entry.profiles import adapter_spec, load_profiles

spec = importlib.util.spec_from_file_location("schema_check", ROOT / "tools/validate-process-forge-schemas.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
SCHEMA = json.loads((ROOT / "schemas/agent-entry-adapters.schema.json").read_text(encoding="utf-8"))
CONTRACT = load_contract()
COUNT = 0


def check(value):
    global COUNT
    errors = validator.validate_instance(value, SCHEMA, SCHEMA, "$")
    assert not errors, errors
    assert value["delivery"] == value["behavior"] == "unverified"
    COUNT += 1
    return value


def fixture(base):
    root = base / "project"
    (root / ".pf").mkdir(parents=True)
    (root / "sub/deep").mkdir(parents=True)
    (root / "AGENTS.md").write_bytes(CONTRACT.raw)
    (root / ".pf/AGENTS.md").write_bytes(CONTRACT.render(extended=True))
    (root / ".pf/agent-entry.json").write_bytes(encoded(manifest(CONTRACT)))
    return root


def tree(root):
    return {p.relative_to(root).as_posix(): (digest(p.read_bytes()), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def blocked(reason, function):
    try:
        function()
    except EntryError as exc:
        assert exc.reason == reason, (reason, exc.reason)
    else:
        raise AssertionError("expected " + reason)


def plan(root, profile="P-CLAUDE", **kwargs):
    return check(plan_adapter(root, profile_id=profile, route="native-import", **kwargs))


def policy(limit, **changes):
    value = dict(id="fixture", unit="utf8_bytes", scope="chain", selection=["CLAUDE.md", "AGENTS.md"],
                 limit=limit, overflow="truncate", source="explicit", accounting_phase="raw_concat")
    value.update(changes)
    return [value]


def main():
    with tempfile.TemporaryDirectory(prefix="pf-entry-adapters-") as tmp:
        base = Path(tmp)
        for profile, filename, reference in [("P-CLAUDE", "CLAUDE.md", b"@AGENTS.md"),
                                               ("P-GEMINI", "GEMINI.md", b"@./AGENTS.md")]:
            for index, user in enumerate([None, b"User secret, no final newline", BOM + b"# User\r\nkeep\r\n", b"```python\nunclosed"]):
                root = fixture(base / f"{profile}-{index}")
                target = root / filename
                if user is not None:
                    target.write_bytes(user)
                before = tree(root)
                proposed = plan(root, profile)
                assert tree(root) == before
                assert [r["path"] for r in proposed["files"]] == [filename]
                assert "User secret" not in json.dumps(proposed) and str(root) not in json.dumps(proposed)
                blocked("explicit_apply_required", lambda: apply_adapter(root, proposed))
                assert tree(root) == before
                receipt = apply_adapter(root, proposed, apply=True)
                assert receipt["action"] == "applied", receipt
                result = target.read_bytes()
                assert result.count(reference) == 1
                if user is not None:
                    assert result.endswith(user[len(BOM):] if user.startswith(BOM) else user)
                    assert result.startswith(BOM) == user.startswith(BOM)
                budget = proposed["budget"]
                assert budget["single_import_preview_bytes"] == len(result) - len(reference) + len(CONTRACT.raw)
                expanded = result.replace(reference, CONTRACT.raw, 1)
                assert expanded[budget["preview_k_start"]:budget["preview_k_end"]] == CONTRACT.raw
                assert not (root / ("GEMINI.md" if filename == "CLAUDE.md" else "CLAUDE.md")).exists()
                repeat = plan(root, profile)
                assert repeat["status"] == "current"
                current = tree(root)
                assert apply_adapter(root, repeat, apply=True)["action"] == "unchanged"
                assert tree(root) == current
                assert rollback_entry(root, receipt["transaction"], apply=True)["action"] == "rolled_back"
                assert (target.read_bytes() if target.exists() else None) == user
                assert rollback_entry(root, receipt["transaction"], apply=True)["action"] == "unchanged"

        root = fixture(base / "ownership")
        target = root / "CLAUDE.md"
        section = adapter_spec("P-CLAUDE", "native-import")["generated_section"].encode()
        target.write_bytes(BOM + section.replace(b"\n", b"\r\n") + b"# retained\r\n")
        assert plan(root)["status"] == "current"
        for raw in [section * 2, b"```\n" + section, section.replace(b"1.0.0", b"9.0.0"),
                    section.replace(b"@AGENTS.md", b"edited"), b"<!-- PF:ADAPTER:BEGIN broken -->"]:
            target.write_bytes(raw)
            before = tree(root)
            blocked("adapter_managed_content_conflict", lambda: plan(root))
            assert tree(root) == before
        for raw in [b"@AGENTS.md\n", b"Read @./AGENTS.md", b"`@AGENTS.md`", b"```\n@AGENTS.md\n```", section + b"@AGENTS.md"]:
            target.write_bytes(raw)
            before = tree(root)
            blocked("adapter_unmanaged_import_candidate", lambda: plan(root))
            assert tree(root) == before
        target.write_bytes(b"AGENTS.md is mentioned in prose")
        assert plan(root)["status"] == "planned"  # Prose is not an owned import.
        target.write_bytes(b"\xff")
        blocked("unsupported_encoding", lambda: plan(root))
        target.unlink()
        (root / "claude.md").write_bytes(b"case collision")
        blocked("case_collision", lambda: plan(root))
        (root / "claude.md").unlink()
        (root / ".pf/agent-entry.json").write_bytes(encoded(dict(manifest(CONTRACT), schema_version=True)))
        blocked("entry_migration_required", lambda: plan(root))

        root = fixture(base / "preconditions")
        proposed = plan(root)
        altered = copy.deepcopy(proposed)
        altered["files"][0]["path"] = "outside.txt"
        blocked("plan_invalid", lambda: apply_adapter(root, altered, apply=True))
        altered["digest"] = digest(encoded({k: v for k, v in altered.items() if k != "digest"}))
        blocked("plan_stale", lambda: apply_adapter(root, altered, apply=True))
        (root / "CLAUDE.md").write_bytes(b"concurrent")
        blocked("plan_stale", lambda: apply_adapter(root, proposed, apply=True))
        proposed = plan(root)
        (root / "AGENTS.md").write_bytes(CONTRACT.raw + b"late root instruction")
        before = tree(root)
        blocked("plan_stale", lambda: apply_adapter(root, proposed, apply=True))
        assert tree(root) == before
        (root / "extra.md").write_bytes(b"first")
        proposed = plan(root, budget_policy=policy(100000, selection=["extra.md", "CLAUDE.md", "AGENTS.md"]))
        (root / "extra.md").write_bytes(b"second")
        blocked("plan_stale", lambda: apply_adapter(root, proposed, apply=True))

        for label in ["staged", "replaced:CLAUDE.md", "dependency"]:
            root = fixture(base / ("fault-" + label.replace(":", "-")))
            def fault(event, tx):
                if label == "dependency" and event == "staged":
                    (root / "AGENTS.md").write_bytes(CONTRACT.raw + b"concurrent user instruction")
                elif event == label:
                    raise EntryError("fixture_fault")
            result = apply_adapter(root, plan(root), apply=True, _fault=fault)
            assert result["action"] == "incomplete", result
            assert pending(root) == [result["transaction"]]
            assert "entry_transaction_incomplete" in plan(root)["blockers"]
            assert rollback_entry(root, result["transaction"], apply=True)["action"] == "rolled_back"
            assert not (root / "CLAUDE.md").exists() and not pending(root)

        root = fixture(base / "rollback-conflict")
        receipt = apply_adapter(root, plan(root), apply=True)
        (root / "CLAUDE.md").write_bytes(b"later user edit")
        before = tree(root)
        blocked("rollback_conflict", lambda: rollback_entry(root, receipt["transaction"], apply=True))
        assert tree(root) == before

        root = fixture(base / "budget")
        (root / "AGENTS.md").write_bytes(CONTRACT.raw + b"required tail" * 40)
        before = tree(root)
        proposed = plan(root, budget_policy=policy(0))
        assert "entry_contract_would_truncate" in proposed["blockers"]
        blocked("entry_contract_would_truncate", lambda: apply_adapter(root, proposed, apply=True))
        assert tree(root) == before
        size = len(adapter_spec("P-CLAUDE", "native-import")["generated_section"].encode())
        proposed = plan(root, budget_policy=policy(size + len(CONTRACT.raw)))
        assert proposed["blockers"] == ["required_instructions_would_truncate"]
        assert plan(root, budget_policy=policy(1, overflow="warn"))["budget"]["raw_policy"]["policies"][0]["warning"]
        assert plan(root, budget_policy=policy(None))["budget"]["status"] == "budget_unverified"
        assert tree(root) == before

        root = fixture(base / "guides")
        before = tree(root)
        for cwd, relative in [(".", "./AGENTS.md"), ("sub/deep", "../../AGENTS.md")]:
            guide = check(adapter_guide(root, profile_id="P-AIDER", route="explicit-read", cwd=cwd))
            assert guide["argv"] == ["aider", "--read", relative]
            assert (root / cwd / relative).resolve() == root / "AGENTS.md"
        for p in load_profiles()["profiles"]:
            if p["route"] in {"root-agents", "selected-native-or-import", "selected-native-import"}:
                assert check(adapter_guide(root, profile_id=p["id"], route="root-agents"))["adapter"]["target"] is None
            if p["route"] in {"workspace-agents", "host-carrier"}:
                guide = check(adapter_guide(root, profile_id=p["id"], route="prerequisites"))
                assert guide["argv"] is None and guide["adapter"]["target"] is None
        negative = check(adapter_guide(root, profile_id="P-OPENCLAW-EMBEDDED", route="prerequisites",
                                        observation={"schema_version": 1, "workspace_matches": False, "context_mode": "lightweight", "injection": "disabled"}))
        assert {"workspace_mismatch", "full_context_mode_required", "instruction_injection_disabled"} <= set(negative["blockers"])
        blocked("adapter_guidance_only", lambda: plan_adapter(root, profile_id="P-CODEX", route="root-agents"))
        blocked("adapter_route_invalid", lambda: plan_adapter(root, profile_id="P-AIDER", route="native-import"))
        blocked("unsupported_profile", lambda: plan(root, "P-UNKNOWN"))
        blocked("unsupported_path", lambda: adapter_guide(root, profile_id="P-AIDER", route="explicit-read", cwd="../"))
        assert tree(root) == before
        (root / "GEMINI.md").write_text("@./AGENTS.md\n", encoding="utf-8")
        assert "adapter_route_conflict" in check(adapter_guide(root, profile_id="P-GEMINI", route="root-agents"))["blockers"]

        root = fixture(base / "cli")
        before = tree(root)
        def cli(*args):
            out = subprocess.run([sys.executable, "-B", str(ROOT / "bin/pf.py"), "agent-entry", *args,
                                  "--project-root", str(root)], capture_output=True, text=True, encoding="utf-8")
            return out.returncode, json.loads(out.stdout)
        code, value = cli("adapter-plan", "--profile", "P-GEMINI", "--route", "native-import")
        assert code == 0
        check(value)
        code, guide = cli("adapter-guide", "--profile", "P-AIDER", "--route", "explicit-read", "--cwd", "sub/deep")
        assert code == 0
        check(guide)
        assert tree(root) == before
        file = base / "plan.json"
        file.write_bytes(encoded(value))
        assert cli("adapter-apply", "--plan-file", str(file))[0] == 1
        assert tree(root) == before
        code, applied = cli("adapter-apply", "--plan-file", str(file), "--apply")
        assert code == 0 and applied["action"] == "applied"
        assert cli("rollback", "--transaction", applied["transaction"], "--apply")[0] == 0
        assert not (root / "GEMINI.md").exists()
    print(f"PASS agent entry adapters: {COUNT} schema-checked plans/guides; ownership, no-write, budgets, stale inputs, fault recovery, rollback and CLI. Native delivery unverified.")


if __name__ == "__main__":
    main()
