"""Regression coverage for task objectives emitted by the existing YAML dumper."""

from pathlib import Path

import pytest

from processforge_core.common.request_scope import safe_load
from processforge_core.common.yaml_dump import dump_yaml, format_scalar
from processforge_core.common.yaml_io import load_yaml_document


def test_multiline_task_objective_loads_without_scanner_error(tmp_path: Path) -> None:
    assignment = {
        "id": "multiline-objective",
        "objective": (
            "Repair the existing task serializer.\n"
            "Preserve the assignment's evidence and lifecycle.\n"
        ),
        "status": "ready",
    }
    path = tmp_path / "assignment.yaml"
    path.write_text(dump_yaml(assignment) + "\n", encoding="utf-8")

    assert load_yaml_document(path) == assignment


@pytest.mark.parametrize(
    "text",
    [
        "first\nsecond",
        "\nfirst\n\nsecond\n\n",
        "first\rsecond\r\nthird\tend",
        'Worker\'s "objective" uses C:\\tasks\\next\nKeep \\n literal.',
        "Задача 😀\nСледующая строка",
        "first\u2028second\u2029third",
        *[f"before{chr(code)}after" for code in range(0x20)],
        *[f"before{chr(code)}after" for code in range(0x7F, 0xA0)],
        "'quoted'",
        '"quoted"',
        ",entry",
        "...",
        "- item",
        "? key",
        "&anchor",
        "*alias",
        "!tag",
        "%directive",
        "@reserved",
        "`reserved",
        ">folded",
        "|literal",
    ],
)
def test_objective_and_list_scalar_round_trip(text: str) -> None:
    document = {"objective": text, "values": [text]}

    assert safe_load(dump_yaml(document)) == document


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("ordinary objective", "ordinary objective"),
        ("worker's objective", "worker's objective"),
        ('say "hello"', 'say "hello"'),
        ("", '""'),
        ("true", "'true'"),
        ("a: b", "'a: b'"),
        ("worker's: objective", "'worker''s: objective'"),
        ("a # b", "'a # b'"),
        ("[entry]", "'[entry]'"),
        ("C:\\tasks\\next", "'C:\\tasks\\next'"),
        (" leading ", "' leading '"),
    ],
)
def test_existing_safe_string_formats_are_preserved(value: str, expected: str) -> None:
    assert format_scalar(value) == expected
    assert safe_load(dump_yaml({"value": value})) == {"value": value}
