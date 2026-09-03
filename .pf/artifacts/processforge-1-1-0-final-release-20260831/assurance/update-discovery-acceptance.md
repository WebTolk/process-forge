# Acceptance: update discovery для 1.1.0

## Подтверждено

- `updates/processforge-update-index.yaml` публикует stable latest `1.1.0` и
  production manifest URL в WebTolk/process-forge.
- `1.2.0` и `1.2.1` отсутствуют в production update index и changelog.
- `smoke_update_sites_schema`, `smoke_update_candidate_discovery`,
  `smoke_update_stage_verify_apply_file_provider`,
  `smoke_core_update_manifest`, `smoke_project_pf_upgrade_assessment_boundary`
  и `smoke_no_production_example_update_urls` — PASS.
- Миграция `1.0.2 -> 1.1.0` объявлена необязательной и вынесена в
  `updates/migrations/1.1.0-stable-release.md`.

## Условие финального PASS

Точный SHA-256/размер и immutable asset URL могут быть проверены только после
exact-tag сборки. На release-delivery обязательны
`smoke_stable_update_manifest_schema.py`,
`smoke_stable_update_manifest_points_to_release.py` и проверка реального
upgrade из извлечённого 1.0.2 fixture/архива.
