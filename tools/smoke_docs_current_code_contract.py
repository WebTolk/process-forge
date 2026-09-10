#!/usr/bin/env python3
"""Regression coverage for public documentation and the current CLI contract."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import shlex
import sys
from pathlib import Path
from urllib.parse import unquote

import yaml


ROOT = Path(__file__).resolve().parents[1]
DOC_ROOTS = [ROOT / "docs", ROOT / "prompts", ROOT / "templates"]
FENCE_LANGUAGES = {"", "bash", "sh", "shell", "console", "text", "powershell", "ps1"}


def document_paths() -> list[Path]:
    return sorted(set(ROOT.glob("*.md")) | {path for root in DOC_ROOTS for path in root.rglob("*.md")})


def load_processforge_module():
    path = ROOT / "tools" / "processforge.py"
    spec = importlib.util.spec_from_file_location("processforge_docs_contract", path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load parser module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def iter_markdown_fences(text: str) -> list[tuple[str, list[str]]]:
    blocks: list[tuple[str, list[str]]] = []
    language = ""
    lines: list[str] = []
    in_block = False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            if in_block:
                blocks.append((language, lines))
                language, lines, in_block = "", [], False
            else:
                language, lines, in_block = stripped[3:].strip().lower(), [], True
            continue
        if in_block:
            lines.append(raw_line.rstrip())
    return blocks


def command_lines(lines: list[str]) -> list[str]:
    """Join shell continuations while retaining only command-looking lines."""
    commands: list[str] = []
    pending = ""
    for raw in lines + [""]:
        line = raw.strip()
        if not pending and (not line or line.startswith(("#", "//"))):
            continue
        if pending:
            line = pending + " " + line
            pending = ""
        if line.endswith(("\\", "`")):
            pending = line[:-1].rstrip()
            continue
        commands.append(line)
    return commands


def cli_tokens(line: str) -> list[str] | None:
    line = re.sub(r"^\s*(?:[$>]\s*)", "", line)
    # Ignore prose before tokenizing: apostrophes outside commands are not shell errors.
    if not re.match(r"^(?:python(?:3|\.exe)?|py|pf)(?:\s|$)", line):
        return None
    line = re.sub(r"<[^>]+>|\$\{[^}]+\}", "DOC_VALUE", line)
    try:
        tokens = shlex.split(line, posix=True)
    except ValueError as exc:
        raise AssertionError(f"malformed shell example: {line}: {exc}") from exc
    if not tokens:
        return None
    if tokens[0] == "pf":
        return tokens[1:]
    if tokens[0] in {"python", "python3", "python.exe", "py"}:
        index = 2 if len(tokens) > 1 and tokens[1] == "-3" else 1
        if len(tokens) > index and tokens[index].replace("\\", "/").rsplit("/", 1)[-1] in {"pf.py", "processforge.py"}:
            return tokens[index + 1:]
    return None


def placeholder_value(flag: str) -> str:
    if flag in {"--type", "--project-type"}:
        return "generic"
    if flag == "--status":
        return "passed"
    if flag == "--kind":
        return "work"
    return "placeholder"


def normalize_cli_tokens(tokens: list[str]) -> list[str]:
    normalized: list[str] = []
    previous_flag = ""
    for token in tokens:
        if token == "DOC_VALUE" or (token.startswith("<") and token.endswith(">")):
            token = placeholder_value(previous_flag)
        elif "<" in token and ">" in token:
            token = re.sub(r"<[^>]+>", placeholder_value(previous_flag), token)
        if token.startswith("--"):
            previous_flag = token.split("=", 1)[0]
        elif previous_flag and not token.startswith("-"):
            previous_flag = ""
        normalized.append(token)
    return normalized


def check_command_docs(parser) -> int:
    checked = 0
    for path in document_paths():
        for language, lines in iter_markdown_fences(path.read_text(encoding="utf-8")):
            if language not in FENCE_LANGUAGES:
                continue
            for line in command_lines(lines):
                args = cli_tokens(line)
                if args is None:
                    continue
                args = normalize_cli_tokens(args)
                if not args:
                    continue
                stderr = io.StringIO()
                try:
                    with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stderr):
                        parser.parse_args(args)
                except SystemExit as exc:
                    if exc.code == 0:
                        checked += 1
                        continue
                    detail = stderr.getvalue().strip()
                    raise AssertionError(
                        f"{path.relative_to(ROOT)}: CLI example rejected ({detail}): {line}"
                    ) from exc
                checked += 1
    if checked < 500:
        raise AssertionError(f"insufficient public CLI coverage: only {checked} examples checked")
    return checked


def check_local_links() -> int:
    checked = 0
    link_pattern = re.compile(r"(?<!!)!?\[[^]]*\]\(([^)]+)\)")
    for path in document_paths():
        for raw_target in link_pattern.findall(path.read_text(encoding="utf-8")):
            target = raw_target.strip().split(' "', 1)[0]
            if not target or target.startswith("#") or any(marker in target for marker in ("<", ">", "${")):
                continue
            if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target:
                continue
            checked += 1
            resolved = ((ROOT / target.lstrip("/")) if target.startswith("/") else (path.parent / target)).resolve()
            if not resolved.exists():
                raise AssertionError(f"broken local link in {path.relative_to(ROOT)}: {raw_target}")
    if checked < 100:
        raise AssertionError(f"insufficient local-link coverage: only {checked} links checked")
    return checked


def assignment_example() -> dict:
    text = (ROOT / "docs" / "concepts" / "assignment-front-matter.md").read_text(encoding="utf-8")
    for language, lines in iter_markdown_fences(text):
        if language == "markdown" and any(line.strip() == "schema_version: 1" for line in lines):
            raw = "\n".join(lines)
            parts = raw.split("---", 2)
            if len(parts) != 3:
                raise AssertionError("assignment front-matter example is malformed")
            data = yaml.safe_load(parts[1])
            if not isinstance(data, dict):
                raise AssertionError("assignment front-matter example must be a mapping")
            return data
    raise AssertionError("assignment front-matter example not found")


def check_assignment_required_outputs(parser_module) -> None:
    data = assignment_example()
    outputs = parser_module.normalize_required_outputs(data.get("required_outputs"))
    if not outputs:
        raise AssertionError("front-matter required_outputs did not normalize to records")
    for item in outputs:
        if not all(str(item.get(key, "")).strip() for key in ("id", "path", "type")):
            raise AssertionError(f"normalized required output is not explicit: {item!r}")
    if parser_module.normalize_required_outputs({"report": {"path": "x"}}):
        raise AssertionError("id-keyed required_outputs must not be accepted")


def json_blocks(text: str) -> list[dict]:
    result: list[dict] = []
    for language, lines in iter_markdown_fences(text):
        if language != "json":
            continue
        try:
            value = json.loads("\n".join(lines))
        except json.JSONDecodeError as exc:
            raise AssertionError(f"invalid JSON concept example: {exc}") from exc
        if isinstance(value, dict):
            result.append(value)
    return result


def check_declarative_contract() -> None:
    from processforge_core.process_execution import ProcessExecutionService

    service = object.__new__(ProcessExecutionService)
    for status in ("passed", "approved", "not_applicable", "pass", "failed"):
        state = service._gate_state({}, "example", [{"kind": "gate", "id": "example", "status": status}], phase="exit")
        assert state["satisfied"] == (status in {"passed", "approved", "not_applicable"}), state
    for relative in ("docs/concepts/declarative-process-execution.md", "docs/ru/concepts/declarative-process-execution.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        if "process_choice_required" not in text or "process_id" not in text or "run_completed" not in text:
            raise AssertionError(f"{relative} omits multi-process choice or completion contract")
        payloads = [item for item in json_blocks(text) if isinstance(item.get("evidence"), list)]
        if not payloads:
            raise AssertionError(f"{relative} has no transition payload example")
        for payload in payloads:
            if not all(payload.get(key) for key in ("project_root", "outcome", "notes")):
                raise AssertionError(f"{relative} transition payload is incomplete")
            evidence = payload["evidence"]
            artifacts = [item for item in evidence if isinstance(item, dict) and item.get("kind") == "artifact"]
            gates = [item for item in evidence if isinstance(item, dict) and item.get("kind") == "gate"]
            if not artifacts or not gates:
                raise AssertionError(f"{relative} payload lacks artifact and gate evidence records")
            if any(not item.get("id") or not item.get("path") for item in artifacts + gates):
                raise AssertionError(f"{relative} evidence is incomplete")
            if any(item.get("status") not in {"passed", "approved", "not_applicable"} for item in gates):
                raise AssertionError(f"{relative} uses an invalid gate status")
            if any(item.get("status") == "pass" for item in gates):
                raise AssertionError(f"{relative} incorrectly accepts gate status pass")
        states = [item for item in json_blocks(text) if "stage" in item and "evidence" not in item]
        if relative == "docs/concepts/declarative-process-execution.md" and not any("artifacts" in item and "gates" in item for item in states):
            raise AssertionError("English state excerpt is not distinguishable from transition payload")


def check_batch_workflow() -> None:
    markers = ["run-create", "task-create", "iteration-add", "task-complete", "run-summary", "run-doctor", "run-complete"]
    for relative in ("docs/getting-started/task-batch-workflow.md", "docs/ru/getting-started/task-batch-workflow.md"):
        text = (ROOT / relative).read_text(encoding="utf-8").lower()
        if any(marker not in text for marker in markers) or "blocking" not in text:
            raise AssertionError(f"{relative} omits an ordinary task-batch lifecycle obligation")
        created, completed = set(), set()
        closed = False
        for language, lines in iter_markdown_fences(text):
            if language not in FENCE_LANGUAGES:
                continue
            for line in command_lines(lines):
                args = cli_tokens(line)
                if not args:
                    continue
                if args[0] == "task-create":
                    created.add(args[args.index("--id") + 1])
                elif args[0] == "task-complete":
                    completed.add(args[args.index("--task") + 1])
                elif args[0] == "run-complete":
                    assert len(created) >= 2 and created <= completed, (relative, created, completed)
                    closed = True
        assert closed, f"{relative} has no executable run completion example"


def check_ru_update_examples() -> None:
    text = (ROOT / "docs/ru/getting-started/update-system.md").read_text(encoding="utf-8")
    for operation in ("core-update plan", "core-update apply"):
        lines = [line for line in text.splitlines() if operation in line and "python" in line]
        if not lines or any("--workplace-root" not in line for line in lines):
            raise AssertionError(f"Russian update example {operation} must request --workplace-root")


def check_checksum_text() -> None:
    text = (ROOT / "docs/validation/validation.md").read_text(encoding="utf-8").lower()
    if "checks only public file inventories" not in text or "does not validate context capsules" not in text:
        raise AssertionError("validation documentation overstates checksum coverage")
    if "capsule-doctor" not in text or "project-context-check" not in text:
        raise AssertionError("validation documentation omits the separate context checks")


def main() -> int:
    parser_module = load_processforge_module()
    assert cli_tokens("It's prose, not a shell command") is None
    assert cli_tokens('python tools/processforge.py run-status --project-root "<project root>"') == ["run-status", "--project-root", "DOC_VALUE"]
    assert cli_tokens('python bin/pf.py --help') == ["--help"]
    assert command_lines(["python bin/pf.py `", "--help"]) == ["python bin/pf.py --help"]
    checked = check_command_docs(parser_module.build_parser())
    links = check_local_links()
    check_assignment_required_outputs(parser_module)
    check_batch_workflow()
    check_declarative_contract()
    check_ru_update_examples()
    check_checksum_text()
    print(f"PASS: public docs match the current PF contract ({checked} CLI examples, {links} local links checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
