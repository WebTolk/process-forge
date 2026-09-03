# Сборка и квалификация ProcessForge 1.1.0

## Итог

Статус: `pass`.

Публичный candidate собран из текущей release surface основного checkout через
изолированный clean Git worktree. Основной dirty checkout не очищался, не
коммитился и не использовался как ложное clean provenance.

## Candidate source

- baseline: `9743839bdc480a1dff603262619a2875c9151320`;
- staged candidate commit: `4f89468`;
- final checksum-normalized candidate commit:
  `8f291ba2f1265d0b426cd4df506d58ba1985a5b5`;
- перенесено измененных/новых public files: `63`;
- candidate Git status перед упаковкой: clean detached HEAD;
- version: `1.1.0`;
- source dirty в sidecar manifest: `false`;
- deterministic build: `true`;
- public release eligible: `true`.

## Архив

- ZIP: `dist/processforge-1.1.0.zip`;
- sidecar: `dist/processforge-1.1.0.manifest.json`;
- ZIP size: `1,338,330` bytes;
- ZIP entries: `898`;
- managed Core files: `897`;
- SHA-256:
  `1530E728BB2C3AEDE7CD57B74347D8B5D08F94A03C98E54AA035B2372992A776`;
- forbidden entries: `0`.

## Source gates

- Python compile: PASS;
- schema validation: PASS;
- public cleanliness: PASS;
- checksum inventory: PASS;
- release-check: PASS;
- `release-test --public --fail-fast --trace-smokes`: PASS,
  `1050.28` seconds;
- ранее проблемный `smoke_long_lived_runtime.py`: PASS, `54.90` seconds.

## Archive gates

- sidecar schema/provenance: PASS;
- archive/manifest file list parity: PASS, `898` entries;
- archive/current clean candidate file hash parity: PASS;
- extracted `bin/pf.py --help`: PASS;
- extracted `tools/processforge.py --help`: PASS;
- full extracted public release-test: PASS, `1029.93` seconds.

## Обновление с официального 1.0.2

Проверен GitHub release asset `v1.0.2/processforge.zip`:

- published SHA-256:
  `3F9E14EAEF5BCB792E5E1CC182C1ED1BC45B5888D600BB04D2AEF3A959A14E9B`;
- old entries: `810`;
- old-only paths относительно 1.1.0: `0`;
- initial status: `not_installed`, потому что 1.0.2 не содержит managed Core
  manifest;
- target-side plan из 1.1.0: `planned`, added `897`, blockers `0`;
- apply без `--confirm`: rejected с `confirm_required`;
- apply с `--confirm`: `applied`, version `1.1.0`;
- post-update Core status: `installed`, manifest files `897`, incomplete update
  `false`;
- installed checksum inventory: PASS;
- installed release-check: PASS;
- installed MCP Codex contract: PASS;
- installed user-like Garage path: PASS;
- installed snapshot-authorized SQLite FTS5 search: PASS;
- installed Runtime Task Scheduler/Codex MCP lifecycle contract: PASS.

Переход является bootstrap overlay: 1.0.2 не знает owned-file manifest, поэтому
перед первым apply документация требует отдельную резервную копию Core. Начиная
с установленного 1.1.0 последующие обновления используют полноценный managed
manifest, backup journal и local-modification guards.

## Невыполненные действия

- основной checkout не коммитился;
- tag и GitHub release не создавались;
- установленный системный Core не обновлялся этим package build;
- release worktree сохранен до завершения независимого review.
