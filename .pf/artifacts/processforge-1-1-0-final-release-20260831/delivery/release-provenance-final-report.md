# Финальный provenance ProcessForge 1.1.0

Статус: `pass`

## Источник

- source commit: `07b1fb68011f5928be824f0c7343322992cf809a`
- source tree: `6a401826a4184191ee0d85d19efb74046def3790`
- annotated tag: `v1.1.0`
- удалённый peeled tag: `07b1fb68011f5928be824f0c7343322992cf809a`
- GitHub Release: https://github.com/WebTolk/process-forge/releases/tag/v1.1.0

Старый удалённый тег `v1.1.0`, указывавший на прежний RC-коммит, удалён с
разрешения оператора и заменён финальным annotated tag. Объекта GitHub Release
для старого тега не существовало.

## Артефакты

- `processforge-1.1.0.zip`: 910 файлов, 1 351 354 байта;
- SHA-256 ZIP:
  `81c3c6708efc3c2a68882d16e716dc49749734c81d44f598767fdbd36a32d8be`;
- `processforge-1.1.0.manifest.json`: 166 211 байт, GitHub digest
  `257b9cb2770e08adf85b1cd0ac7afb31cc6bb1331699188042b8d98443639c3e`;
- sidecar объявляет `release_eligible: true`, `source.dirty: false` и точный
  source commit/tag;
- нейтральный `processforge.zip`, отдельно собранный из того же чистого
  checkout, побайтно совпадает с версионным ZIP; его sidecar корректно хранит
  нейтральное имя архива;
- исторический sidecar в `release/1.1.0/` совпадает с опубликованным sidecar;
- stable manifest находится вне ZIP и ссылается на immutable GitHub assets.

## Проверки

- source public `release-test`: 186/186 PASS, 975,73 с;
- физическая проверка archive/sidecar/root: PASS, 910/910 файлов;
- полный `release-test` на постоянной распаковке ZIP: все 185 исполняемых
  checks PASS; единственный WARN — ожидаемый пропуск `git diff --check` вне Git
  checkout; итог `PASS with warnings`, 937,38 с;
- первый обёрнутый archive-run дал один неидентифицированный FAIL, поскольку
  обёртка сохранила только хвост и удалила временную распаковку; повторный
  fail-fast с сохранёнными JSON/trace полностью прошёл, включая
  `smoke_long_lived_runtime`;
- stable schema, immutable URL/hash/size, отсутствие `example.com`, tag parity,
  public cleanliness и отсутствие release metadata внутри ZIP: PASS.

## Обновление 1.0.2 -> 1.1.0

Использован официальный публичный asset `v1.0.2` с SHA-256
`3f9e14eaef5bcb792e5e1cc182c1ed1bc45b5888d600bb04d2aef3a959a14e9b`.
Извлечённая версия подтверждена как `1.0.2`; финальный updater построил план без
blockers, применил его только с `--confirm`, создал ownership manifest и выдал
установленную версию `1.1.0`. После применения checksum и release-check — PASS.
