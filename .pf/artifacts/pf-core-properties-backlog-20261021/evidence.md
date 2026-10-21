# Подтверждённый источник версии

Исследован точный поставляемый commit `cc690b263b65daaa0e85a21186de89944b1064a9`.
Текущие несвязанные dirty-файлы checkout не являются источником этих фрагментов.

## tools/processforge.py

```text
457: PROCESSFORGE_VERSION = "1.2.0"
3605:     version_file = ROOT / "VERSION"
3606:     version = version_file.read_text(encoding="utf-8", errors="replace").strip() if version_file.is_file() else PROCESSFORGE_VERSION
```

## tools/pf_runtime/monitor.py

```text
843:         snapshot = collect_snapshot(workplace, core.PROCESSFORGE_VERSION)
```

## tools/pf_runtime/service.py

```text
39: RUNTIME_VERSION = "1.0.0-poc"
142:         "processforge_core_version": getattr(core, "PROCESSFORGE_VERSION", ""),
1045:     payload["installed_pf"] = {"version": str(getattr(core, "PROCESSFORGE_VERSION", ""))}
```

## src/processforge_core/common/release_identity.py

```text
6: RELEASE_ARCHIVE_VERSION = "1.3.0-alpha1"
```

## VERSION

```text
1: 1.3.0-alpha1
```

VERSION/manifest и все 1460 файлов установленной поставки подтверждены
в завершённом операторском отчёте pf-device-dev-update-20261021.
Фрагменты и хеши сохранены без приватных путей устройства.
