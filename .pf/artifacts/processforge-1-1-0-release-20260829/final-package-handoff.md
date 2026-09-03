# Handoff пакета ProcessForge 1.1.0 на тестирование

## Пакет

- archive: `dist/processforge-1.1.0.zip`;
- sidecar: `dist/processforge-1.1.0.manifest.json`;
- version: `1.1.0`;
- size: `1,338,330` bytes;
- entries: `898`;
- SHA-256:
  `1530E728BB2C3AEDE7CD57B74347D8B5D08F94A03C98E54AA035B2372992A776`;
- release eligible: `true`;
- deterministic: `true`;
- source dirty: `false`;
- forbidden entries: `0`.

## Квалификация

- source public release-test: PASS, `1050.28` seconds;
- full extracted archive release-test: PASS, `1029.93` seconds;
- manifest/ZIP/hash parity: PASS;
- official GitHub v1.0.2 asset SHA-256 verified;
- target-side 1.0.2 -> 1.1.0 plan/confirm/apply: PASS;
- installed checksum/release-check: PASS;
- installed MCP contract, Garage path, FTS5 search and Runtime/MCP lifecycle
  smokes: PASS;
- independent review: no package defects; procedural observations dispositioned.

## Scope boundary

Это готовый пакет для внешнего тестирования. Source commit/push, tag и GitHub
release не выполнялись. Основной dirty checkout сохранен без очистки и без
коммита; release provenance принадлежит изолированному candidate commit
`8f291ba2f1265d0b426cd4df506d58ba1985a5b5`.
