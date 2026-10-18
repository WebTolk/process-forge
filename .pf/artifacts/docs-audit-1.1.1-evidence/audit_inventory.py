"""Private audit helper: inspect docs/parser only; never dispatch CLI commands."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import re
import shlex
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import processforge as core


def main() -> None:
    parser = core.build_parser()
    paths = sorted(set(
        list(ROOT.glob("*.md"))
        + [p for d in ("docs", "prompts", "templates") for p in (ROOT / d).rglob("*.md")]
    ))
    commands, links, documents = [], [], []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()
        documents.append({"path": rel, "lines": len(text.splitlines()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        in_fence = False
        logical, start = "", 0
        for number, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                logical = ""
                continue
            if not in_fence:
                continue
            if not logical:
                start = number
            part = line.strip()
            if part.endswith(("\\", "`")):
                logical += part[:-1] + " "
                continue
            logical += part
            match = re.search(r'(?:pf|processforge)\.py[\"\']?\s+(.+)', logical)
            if match and re.search(r"\bpython(?:3|\.exe)?\b", logical):
                raw = match.group(1)
                normalized = re.sub(r"<[^>]+>", "AUDIT_VALUE", raw)
                normalized = re.sub(r"\$\{[^}]+\}", "AUDIT_VALUE", normalized)
                record = {"path": rel, "line": start, "command": logical}
                try:
                    args = shlex.split(normalized, posix=True)
                    if not re.match(r"^(?:\$\s+)?python(?:3|\.exe)?\s", logical):
                        record.update(status="manual", error="prose mentioning a launcher, not an executable example")
                    elif any(token in {"&&", "|", ">"} for token in args):
                        record.update(status="manual", error="partial command or shell composition")
                    else:
                        captured = io.StringIO()
                        try:
                            with contextlib.redirect_stderr(captured), contextlib.redirect_stdout(captured):
                                parser.parse_args(args)
                            record["status"] = "accepted"
                        except SystemExit as exc:
                            record.update(status="accepted" if exc.code == 0 else "rejected", exit=exc.code,
                                          error=captured.getvalue().strip().splitlines()[-1])
                except ValueError as exc:
                    record.update(status="manual", error=str(exc))
                commands.append(record)
            logical = ""
        for match in re.finditer(r"\[[^\]\n]*\]\(([^)\n]+)\)", text):
            dest = match.group(1).strip().split(' "', 1)[0]
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", dest) or dest.startswith("#"):
                continue
            clean = unquote(dest.split("#", 1)[0].split("?", 1)[0])
            if not clean or any(marker in clean for marker in ("<", ">", "${")):
                continue
            target = (path.parent / clean).resolve() if not clean.startswith("/") else (ROOT / clean.lstrip("/")).resolve()
            links.append({"path": rel, "line": text.count("\n", 0, match.start()) + 1,
                          "target": dest, "exists": target.exists()})
    command_tree = []
    def walk(current: argparse.ArgumentParser, prefix: str) -> None:
        command_tree.append({"command": prefix, "options": sorted(current._option_string_actions)})
        for action in current._actions:
            if isinstance(action, argparse._SubParsersAction):
                for name, child in action.choices.items():
                    walk(child, f"{prefix} {name}".strip())
    walk(parser, "")
    report = {"method": "fenced Python PF invocations; argparse parse only, no dispatch; local file link targets, not anchors",
              "documents": documents, "commands": commands, "local_links": links, "parser_tree": command_tree}
    output = Path(__file__).with_name("inventory.json")
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"documents": len(documents), "commands": len(commands),
                      "accepted": sum(r["status"] == "accepted" for r in commands),
                      "rejected": sum(r["status"] == "rejected" for r in commands),
                      "manual": sum(r["status"] == "manual" for r in commands),
                      "local_links": len(links), "missing_targets": sum(not r["exists"] for r in links),
                      "report": output.relative_to(ROOT).as_posix()}))
    for record in commands:
        if record["status"] != "accepted":
            print(json.dumps(record, ensure_ascii=False))
    for record in links:
        if not record["exists"]:
            print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
