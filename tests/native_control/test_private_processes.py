"""Private process data stays live without widening the captured Core image."""

from __future__ import annotations

import builtins
import importlib.util
import io
import json
import os
import subprocess
import sys
import textwrap
import uuid
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def tmp_path() -> Path:
    root = Path(os.environ["PF_PRIVATE_PROCESS_TEST_ROOT"]) / uuid.uuid4().hex
    root.mkdir(parents=True)
    return root


def load_native() -> Any:
    spec = importlib.util.spec_from_file_location(
        "private_process_native", ROOT / "tools/pf_native_control.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sealed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    native = load_native()
    image = native.NativeImage.__new__(native.NativeImage)
    image.root = tmp_path.resolve()
    image.files = {
        "tools/pinned.py": b"answer = 42\n",
        "processes/core/pinned.yaml": b"id: captured-core\n",
        "processes/user/pinned.yaml": b"id: captured-private\n",
    }
    image._active = False
    # Restore every process-global hook installed by activate at fixture exit.
    monkeypatch.setattr(sys, "meta_path", list(sys.meta_path))
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    monkeypatch.setattr(builtins, "open", builtins.open)
    monkeypatch.setattr(io, "open", io.open)
    monkeypatch.setattr(
        importlib.util,
        "spec_from_file_location",
        importlib.util.spec_from_file_location,
    )
    image.activate()
    return native, image


def physical_write(native: Any, path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with native._PHYSICAL_OPEN(path, "wb") as stream:
        stream.write(raw)


@pytest.mark.parametrize("opener", [builtins, io])
@pytest.mark.parametrize(
    "relative",
    [
        "processes/user/work.yaml",
        "processes/custom/work.yml",
        "processes/user/nested/work.YAML",
        "processes/custom/nested/work.YmL",
    ],
)
def test_private_reads_live_snapshots(sealed: Any, opener: Any, relative: str) -> None:
    native, image = sealed
    path = image.root / relative
    first = "id: first\r\nname: Проверка\r\n".encode()
    physical_write(native, path, first)
    with opener.open(path, "rb") as stream:
        assert stream.read() == first
        assert stream.name == str(path)
    old_snapshot = opener.open(path, "r", encoding="utf-8")
    physical_write(native, path, b"id: second\n")
    with old_snapshot:
        assert old_snapshot.read() == first.decode().replace("\r\n", "\n")
    with opener.open(path, "rt", encoding="utf-8") as stream:
        assert stream.read() == "id: second\n"
    assert relative not in image.files


@pytest.mark.parametrize(
    "relative",
    ["processes/user/pinned.yaml", "processes/core/pinned.yaml", "tools/pinned.py"],
)
def test_accepted_bytes_win_over_disk_drift(sealed: Any, relative: str) -> None:
    native, image = sealed
    path = image.root / relative
    physical_write(native, path, b"replaced on disk\n")
    assert path.read_bytes() == image.files[relative]
    path.unlink()
    assert path.read_bytes() == image.files[relative]


@pytest.mark.parametrize(
    "relative",
    [
        "processes/core/unpinned.yaml",
        "packs/official/example/processes/unpinned.yaml",
        "processes/flat.yaml",
        "processes/userish/unpinned.yaml",
        "processes/user/source.py",
        "processes/custom/source.pyc",
        "processes/user/config.json",
        "tools/unpinned.py",
        "src/unpinned.py",
    ],
)
def test_unrelated_data_and_code_remain_closed(sealed: Any, relative: str) -> None:
    native, image = sealed
    path = image.root / relative
    physical_write(native, path, b"present on disk")
    with pytest.raises(native.NativeControlError):
        path.read_bytes()
    if path.suffix == ".py":
        with pytest.raises(native.NativeControlError):
            importlib.util.spec_from_file_location("unaccepted", path)


@pytest.mark.parametrize("opener", [builtins, io])
@pytest.mark.parametrize("mode", ["w", "wb", "a", "x", "r+", "r+b", "w+", "a+"])
def test_private_writes_and_updates_are_refused(
    sealed: Any, opener: Any, mode: str
) -> None:
    native, image = sealed
    path = image.root / "processes/user/work.yaml"
    physical_write(native, path, b"id: unchanged\n")
    with pytest.raises(native.NativeControlError):
        opener.open(path, mode)
    with native._PHYSICAL_OPEN(path, "rb") as stream:
        assert stream.read() == b"id: unchanged\n"


@pytest.mark.parametrize("option", ["opener", "closefd"])
def test_private_open_options_cannot_escape(sealed: Any, option: str) -> None:
    native, image = sealed
    path = image.root / "processes/custom/work.yaml"
    physical_write(native, path, b"id: safe\n")
    invoked = []

    def escape(path: str, flags: int) -> int:
        invoked.append(path)
        raise AssertionError("custom opener must never execute")

    options: dict[str, Any] = (
        {"opener": escape} if option == "opener" else {"closefd": False}
    )
    with pytest.raises(native.NativeControlError):
        open(path, "rb", **options)
    assert invoked == []


def test_private_binary_text_options_and_missing_files(sealed: Any) -> None:
    native, image = sealed
    path = image.root / "processes/user/work.yaml"
    physical_write(native, path, b"id: safe\n")
    for option in ({"encoding": "utf-8"}, {"errors": "replace"}, {"newline": ""}):
        with pytest.raises(ValueError):
            open(path, "rb", **option)
    path.unlink()
    with pytest.raises(native.NativeControlError):
        path.read_bytes()


@pytest.mark.parametrize(
    "relative",
    [
        "processes/user/../custom/work.yaml",
        "processes/user/nested/../work.yaml",
        "processes/user/../../outside.yaml",
    ],
)
def test_private_traversal_is_refused(sealed: Any, relative: str) -> None:
    native, image = sealed
    for name in (
        "processes/custom/work.yaml",
        "processes/user/work.yaml",
        "outside.yaml",
    ):
        physical_write(native, image.root / name, b"id: aliased\n")
    with pytest.raises(native.NativeControlError):
        open(image.root / relative, "rb")


def test_private_hardlink_is_refused(sealed: Any) -> None:
    native, image = sealed
    source = image.root / "original.yaml"
    target = image.root / "processes/custom/work.yaml"
    physical_write(native, source, b"id: linked\n")
    target.parent.mkdir(parents=True)
    os.link(source, target)
    with pytest.raises(native.NativeControlError):
        target.read_bytes()


@pytest.mark.skipif(os.name != "nt", reason="Windows alternate data streams")
def test_private_alternate_data_stream_is_refused(sealed: Any) -> None:
    native, image = sealed
    source = image.root / "processes/user/work.yaml"
    physical_write(native, source, b"id: base\n")
    stream = Path(str(source) + ":stream.yaml")
    physical_write(native, stream, b"id: alternate\n")
    with pytest.raises(native.NativeControlError):
        stream.read_bytes()


@pytest.mark.parametrize("directory", [False, True])
def test_private_symlinks_are_refused(sealed: Any, directory: bool) -> None:
    native, image = sealed
    source = image.root / "original/work.yaml"
    physical_write(native, source, b"id: linked\n")
    target = image.root / "processes/user/work.yaml"
    target.parent.mkdir(parents=True)
    try:
        if directory:
            link = target.parent / "linked"
            link.symlink_to(source.parent, target_is_directory=True)
            target = link / source.name
        else:
            target.symlink_to(source)
    except OSError as error:
        pytest.skip(f"host cannot create test-owned symlink: {error}")
    with pytest.raises(native.NativeControlError):
        target.read_bytes()


@pytest.mark.skipif(os.name != "nt", reason="Windows junction boundary")
def test_private_directory_junction_is_refused(sealed: Any) -> None:
    native, image = sealed
    source = image.root / "original/work.yaml"
    physical_write(native, source, b"id: linked\n")
    link = image.root / "processes/custom/linked"
    link.parent.mkdir(parents=True)
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(source.parent)],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert link.lstat().st_file_attributes & 0x400
    with pytest.raises(native.NativeControlError):
        (link / source.name).read_bytes()


@pytest.mark.parametrize("change", ["replace_before_open", "mutate_during_read"])
def test_private_read_refuses_identity_or_content_race(
    sealed: Any, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    native, image = sealed
    path = image.root / "processes/user/work.yaml"
    replacement = path.with_name("replacement.yaml")
    physical_write(native, path, b"id: before\n")
    physical_write(native, replacement, b"id: unsafe replacement\n")
    original_open = native._PHYSICAL_OPEN
    events = []

    class MutatingRead:
        def __init__(self, stream: Any) -> None:
            self.stream = stream

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *args: Any) -> None:
            self.stream.close()

        def fileno(self) -> int:
            return self.stream.fileno()

        def read(self, size: int) -> bytes:
            raw = self.stream.read(size)
            # Same file and size: force a distinguishable metadata change too.
            try:
                writer = original_open(path, "r+b")
            except PermissionError:
                events.append("writer_denied")
                return raw
            with writer:
                writer.write(b"id: unsafe\n")
            info = path.stat()
            os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 2_000_000_000))
            events.append("mutated")
            return raw

    def racing_open(file: Any, mode: str) -> Any:
        assert Path(file) == path and mode == "rb"
        if change == "replace_before_open":
            try:
                os.replace(replacement, path)
            except PermissionError:
                events.append("replacement_denied")
                raise
            events.append("replaced")
        stream = original_open(file, mode)
        return MutatingRead(stream) if change == "mutate_during_read" else stream

    monkeypatch.setattr(native, "_PHYSICAL_OPEN", racing_open)
    try:
        result = path.read_bytes()
    except native.NativeControlError:
        assert events in (["mutated"], ["replaced"], ["replacement_denied"])
    else:
        assert events == ["writer_denied"]
        assert result == b"id: before\n"


@pytest.mark.skipif(os.name != "nt", reason="Windows creation-time stat semantics")
def test_private_same_length_write_with_preserved_times(
    sealed: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    native, image = sealed
    path = image.root / "processes/user/work.yaml"
    original = b"id: before\n"
    replacement = b"id: unsafe\n"
    assert len(original) == len(replacement)
    physical_write(native, path, original)
    initial = path.stat()
    fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    receipt: dict[str, Any] = {
        "before": {field: getattr(initial, field) for field in fields},
        "writer_denied": False,
    }
    physical_open = native._PHYSICAL_OPEN

    class ControlledRead:
        def __init__(self, stream: Any) -> None:
            self.stream = stream
            self.writer: Any = None

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *args: Any) -> None:
            # Retain an admitted writer through all post-read validation.
            self.stream.close()
            if self.writer is not None:
                self.writer.close()

        def fileno(self) -> int:
            return self.stream.fileno()

        def read(self, size: int) -> bytes:
            prefix = os.read(self.stream.fileno(), 5)
            try:
                self.writer = physical_open(path, "r+b", buffering=0)
            except PermissionError:
                receipt["writer_denied"] = True
            else:
                self.writer.write(replacement)
                self.writer.flush()
                os.utime(path, ns=(initial.st_atime_ns, initial.st_mtime_ns))
                observed = os.fstat(self.stream.fileno())
                receipt["during_read"] = {
                    field: getattr(observed, field) for field in fields
                }
                receipt["signature_equal"] = receipt["before"] == receipt["during_read"]
                receipt["writer_held_open"] = not self.writer.closed
            return prefix + os.read(self.stream.fileno(), size - len(prefix))

    def controlled_open(file: Any, *args: Any) -> Any:
        assert Path(file) == path
        stream = physical_open(file, *args)
        return ControlledRead(stream)

    monkeypatch.setattr(native, "_PHYSICAL_OPEN", controlled_open)
    try:
        result = path.read_bytes()
        receipt["result"] = result.decode("utf-8")
        receipt["refused"] = False
    except native.NativeControlError:
        result = None
        receipt["refused"] = True
    finally:
        with physical_open(
            image.root / "preserved-time-race.json", "w", encoding="utf-8"
        ) as stream:
            json.dump(receipt, stream, indent=2)
        print(json.dumps(receipt, sort_keys=True))
    if receipt["writer_denied"]:
        assert result == original
    else:
        assert receipt["refused"], receipt


def test_live_private_catalog_coexists_with_captured_core_and_release_policy(
    tmp_path: Path,
) -> None:
    # A clean interpreter imports the real catalog from captured Core sources.
    # Nothing is read from or written to the installed distribution or workplace.
    script = textwrap.dedent(
        """
        import importlib.util, sys
        from pathlib import Path
        source, fixtures = map(Path, sys.argv[1:])
        spec = importlib.util.spec_from_file_location('catalog_native', source / 'tools/pf_native_control.py')
        native = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = native
        spec.loader.exec_module(native)
        root = fixtures / 'distribution'
        project = fixtures / 'project'
        project.mkdir()
        def put(relative, raw):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with native._PHYSICAL_OPEN(path, 'wb') as stream:
                stream.write(raw)
        put('processes/user/nested/user.yml', b'id: private-user\\nname: First\\n')
        put('processes/custom/custom.yaml', b'id: private-custom\\n')
        put('processes/core/core.yaml', b'id: disk-drift\\n')
        image = native.NativeImage.__new__(native.NativeImage)
        image.root = root.resolve()
        image.files = {
            path.relative_to(source).as_posix(): path.read_bytes()
            for path in (source / 'src').rglob('*.py')
        }
        image.files['processes/core/core.yaml'] = b'id: captured-core\\n'
        image._active = False
        image.activate()
        from processforge_core.process_catalog.models import ProcessCatalogContext
        from processforge_core.process_catalog.service import process_catalog_entries, resolve_process_definition
        from processforge_core.maintenance.release_sources import ReleaseSourcePolicy
        context = ProcessCatalogContext(project, project / '.pf', root, frozenset())
        entries = {entry.process_id: entry for entry in process_catalog_entries(context, strict=True)}
        assert set(entries) == {'private-user', 'private-custom', 'captured-core'}, entries
        assert entries['private-user'].origin == 'user'
        assert entries['private-custom'].origin == 'custom'
        assert entries['captured-core'].origin == 'core'
        assert entries['private-user'].process['name'] == 'First'
        put('processes/user/nested/user.yml', b'id: private-user\\nname: Updated\\n')
        assert resolve_process_definition(context, 'private-user').process['name'] == 'Updated'
        policy = ReleaseSourcePolicy()
        private = {'processes/user/nested/user.yml', 'processes/custom/custom.yaml'}
        candidates = {name for name, _ in policy.release_source_files(root)}
        assert private <= candidates
        assert all(policy.release_path_is_forbidden(name) for name in private)
        eligible = {name for name in candidates if not policy.release_path_is_forbidden(name)}
        assert eligible == {'processes/core/core.yaml'}, eligible
        assert private.isdisjoint(image.files)
        print('private catalog live; Core captured; private release paths forbidden')
        """
    )
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script, str(ROOT), str(tmp_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    (tmp_path / "catalog.stdout.log").write_text(result.stdout, encoding="utf-8")
    (tmp_path / "catalog.stderr.log").write_text(result.stderr, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
