# Handoff: official bundled process packs

Дата: 2026-07-30
Статус: завершено, готово к локальной интеграции

## Доставлено

- first-class distribution layer `packs/official/**`;
- три versioned official packs с manifests и production-ready metadata;
- перенос пяти production process definitions из canonical examples;
- data-driven workplace activation и profiles;
- discovery через `pack-list`, `process-list` и `process-show`;
- защита исполнения неактивных official processes;
- data-driven official software classifier;
- capability resolution и context freshness для активных packs;
- отдельная JSON Schema, validators, policies и public inventory;
- EN/RU concepts и getting-started documentation;
- десять новых official-pack smokes и адаптация regression smokes.

## Текущая проверка

Полный public release-test и независимый implementation review завершились
PASS. Новый `dist/processforge.zip` собран: 777 файлов, включая 30 official-pack
entries и отдельную schema; старых canonical example-domain entries нет.
Полный release-test внутри распакованного архива завершился PASS за 474,77 с.

## Остаточные ограничения

- knowledge manifests в software pack пока описывают identities без ресурсов;
- freshness diagnostics отдельно fingerprint-ят pack manifest/classifiers, но
  не каждый process/knowledge YAML;
- self-hosted assignment capsule блокируется неполным project capability
  registry, без waiver; отдельный official-pack probe capsule проходит.

Commit и push в это задание не входят.
