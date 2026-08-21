# Specialization Path Leak Audit

## Итог

Причина утечки локального absolute workplace path находится в `tools/processforge.py`, в сборке `selected_specializations` внутри `resolve_specialization_context()`.

Путь попадал в публичный project-context snapshot через цепочку:

- `build_project_context_snapshot()` читает `specializations` из `.pf/process-forge.yaml`: `tools/processforge.py:9758`
- вызывает `resolve_specialization_context(...)`: `tools/processforge.py:9759-9766`
- затем без дополнительной санитаризации копирует результат в публичный snapshot:
  - `resolved_context`: `tools/processforge.py:9926`
  - `active_resource_profile`: `tools/processforge.py:9927`
  - `selected_specializations`: `tools/processforge.py:9930`

## Producer

Точный producer поля:

`tools/processforge.py:4849-4859`

Там создается запись `selected_specializations[]`. В уязвимом варианте ветка для workplace specialization, не лежащей внутри `project_root`, возвращала `str(spec.get("__manifest_path") or "")`, то есть абсолютный путь к private workplace manifest.

В текущем прочитанном состоянии файла это место уже выглядит закрытым: для внешнего пути используется `"<private-specialization-ref>"` на `tools/processforge.py:4859`.

## Остаточный риск

Есть второй похожий путь утечки, если выбранная workplace specialization содержит `parameters`:

`resolve_project_parameters()` передает `__manifest_path` в `add_parameter_source()` для specialization source:

`tools/processforge.py:8523-8531`

`parameter_source_record()` при отсутствии `display_path` пишет absolute path для пути вне `project_root`, даже если `private=True`:

`tools/processforge.py:8401-8410`

То есть минимальная правка для `selected_specializations[].path` закрывает основной reproduced leak, но не полностью закрывает тот же класс ошибки для `parameter_resolution.sources[].path`.

## Минимальная remediation

Платформенно-нейтрально:

1. Оставить/применить redaction в `resolve_specialization_context()`:
   - если `__manifest_path` лежит внутри `project_root`, писать `rel(...)`;
   - иначе писать `"<private-specialization-ref>"`;
   - не записывать `str(Path)` для private workplace paths.

2. Исправить `parameter_source_record()`:
   - если `private=True` и `display_path` не передан, а `path` не находится внутри `project_root`, писать общий placeholder вроде `"<private-source-ref>"`;
   - если нужен более точный источник для specialization, передавать `display_path="<private-specialization-ref>"` из `resolve_project_parameters()`.

3. Не менять `path_ref` модель для knowledge resources: там уже есть публичная indirection через registry/package refs, и schema допускает `path_ref`.

## Regression Assertion

Целевой smoke/regression должен создавать временные `project_root` и `workplace_root`, регистрировать specialization только во workplace, явно выбрать ее в project manifest, затем построить snapshot через `build_project_context_snapshot()`.

Проверки:

- сериализованный snapshot не содержит `str(workplace_root)`;
- сериализованный snapshot проходит `is_public_path_safe(...)`;
- `snapshot["selected_specializations"][0]["path"] == "<private-specialization-ref>"`;
- `snapshot["active_resource_profile"]["selected_specializations"][0]["path"] == "<private-specialization-ref>"`;
- если specialization содержит `parameters`, `parameter_resolution.sources` для `specialization:*` имеет `private: true` и не содержит absolute path.

## Schema Note

`schemas/project-context-snapshot.schema.json` сейчас не предотвращает этот класс ошибок: `selected_specializations` объявлены как массив объектов с `additionalProperties: true`, а `path` не ограничен. Поэтому основная защита должна быть в producer-level redaction и regression test, не только в schema validation.