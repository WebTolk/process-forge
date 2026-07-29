# Review: Domain-Neutral Core Boundary

Дата: 2026-07-29
Вердикт: PASS WITH OBSERVATIONS

## Проверено

- default workplace не содержит и не активирует domain resources;
- core process/prompt/package catalogs предметно нейтральны;
- domain processes, prompts, docs, packages и seeds находятся только в
  explicit optional example packs;
- project classification зависит от registry data, а не от встроенных
  technology filename rules;
- classifier schemas реально проверяются локальным validator;
- snapshot freshness реагирует на изменение классификации;
- hardcode policy и девять новых smokes включены в public release gate;
- старые capability, specialization, overrides, evolve, orchestration и
  software-pack regression smokes не удалены;
- собранный ZIP соответствует source root и проходит полный extracted gate.

## Evidence

- `.pf/runtime/release-test/latest-report.json`: `PASS`, 128/128;
- `dist/processforge.zip`: 762 файла;
- `dist/processforge.manifest.json`: список и hashes подтверждены;
- full `release-archive-test`: `RESULT: PASS`;
- `checksums/processforge.sha256`: актуален;
- `git diff --check`: PASS.

## Наблюдения

1. Missing/malformed active classifier пока молча исключается из загрузки и
   приводит к `unclassified`; нужен отдельный doctor failure.
2. Duplicate classifier ids пока агрегируются без формальной scope precedence.
3. Assignment capsule этого engagement заблокирован отсутствующими workplace
   capability ids; это ограничение локальной process-конфигурации, не release
   waiver.

Блокирующих дефектов по acceptance criteria мастер-задания не найдено.
