# Independent review: official bundled process packs

Дата: 2026-07-30
Reviewer: `official_pack_reviewer`
Статус: PASS

## Первичная рекомендация

`FAIL` до исправления material findings.

Reviewer подтвердил kernel neutrality, manifest-driven profile activation,
classifier loading, generic-profile isolation, отсутствие example shadowing,
10/10 новых smokes, schema/public/checksum/catalog проверки. При этом были
обнаружены:

1. `HIGH`: `process-doctor` разрешал companion prompt/docs/example только от
   project root, а не от official pack root.
2. `HIGH`: execution gate блокировал project custom override, если неактивный
   official pack содержал тот же process ID.
3. `MEDIUM`: manifest-declared knowledge packages не попадали в активный
   specialization/context profile.
4. `MEDIUM`: EN/RU docs использовали отсутствующий `process-show --workplace`.
5. `MEDIUM`: прямой YAML path official process терял origin/pack/activation
   metadata.
6. `LOW`: public process-list выводил внутренние `core/user/custom` вместо
   `kernel/workspace/project`.
7. Release archive был stale и требовал пересборки после завершения assurance.

## Исправления

- Companion paths official process разрешаются от эффективного
  `ProcessDefinitionRef.root`; `example_required: false` учитывается обоими
  doctor validators.
- Activation gate проверяет эффективного победителя catalog precedence и
  блокирует только реально выбранный неактивный `origin: official`.
- Активные manifests декларативно добавляют `provides.knowledge_packages` в
  specialization/context, а их knowledge manifests входят в package index.
- `process-show`/`process-describe` получили workplace override.
- Direct YAML resolution сопоставляет путь с official manifest и сохраняет
  metadata.
- Public origin vocabulary нормализована; старые значения оставлены только как
  совместимые filter aliases.
- Software manifest дополнен полным рекурсивным объединением capabilities:
  включая `architecture`, `investigation` и `process_coordination`.
- Official-pack smokes усилены проверками doctor, custom override precedence,
  knowledge activation, direct path, workplace override и public origins.

## Повторная проверка

Независимый повторный review: `PASS` для implementation slice.

Подтверждено:

- 5/5 official processes проходят `process-doctor --contract-only` в
  изолированных workplaces;
- custom override выигрывает catalog precedence и не блокируется official
  activation gate;
- software context активирует все шесть knowledge package IDs;
- `process-show --workplace` и direct official YAML сохраняют корректные
  activation/pack metadata;
- public process-list выводит `kernel`, а не внутренний `core`;
- recursive software capability union точный: 7 declared == 7 required;
- 10/10 official smokes, schema, public cleanliness, checksum, catalog doctor,
  compilation, specialization regressions и `git diff --check` — PASS.

После review release delivery завершён: новый ZIP содержит 777 файлов,
manifest совпадает 777/777, official packs представлены 30 entries, legacy
domain examples отсутствуют. Полный extracted archive test завершён
`RESULT: PASS` за 474,77 с.

Остаточные риски:

- шесть knowledge manifests остаются catalog identities с `resources: []`;
- freshness keys активного pack явно охватывают manifest и classifiers, но не
  каждый process/knowledge YAML отдельно.
