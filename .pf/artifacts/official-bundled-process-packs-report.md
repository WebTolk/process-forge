# Official bundled process packs: отчёт о реализации

Дата: 2026-07-30
Статус: завершено, все обязательные release gates PASS

## Результат

ProcessForge получил отдельный first-class слой `packs/official/**`: дистрибутив
может поставлять production-ready процессы, не превращая их в зависимости
ядра. Domain-neutral kernel означает отсутствие предметных решений в runtime,
а не пустой дистрибутив. Ядро знает только общий контракт process pack,
манифест, registry, activation и precedence; software/content/verification
поставляются как данные.

Это соответствует аналогии со встроенными расширениями Joomla: расширение
может входить в официальный дистрибутив, иметь поддерживаемый lifecycle и быть
готовым к эксплуатации, оставаясь отделённым от Joomla Framework/CMS kernel.
Так же и official process pack поставляется вместе с PF, но имеет
`core_runtime_dependency: false` и активируется явно.

## Модель official pack

Каждый пакет расположен в `packs/official/<pack>/` и имеет отдельный
`package.yaml` со стабильным dotted ID, версией, `origin: official`,
`bundled: true`, `production_ready: true`, `core_runtime_dependency: false`,
activation profiles и декларативным `provides`. Отдельная схема
`schemas/process-pack-manifest.schema.json` не смешивает process packs с
knowledge-package manifests.

Созданы пакеты:

- `processforge.official.software-development`;
- `processforge.official.content-workflow`;
- `processforge.official.verification`.

Из `examples/domain-packs/**` перенесены все канонические process definitions,
prompts, process docs, package manifests и software classifier. Сохранены
process ID и версии:

- `software-feature-development` 1.1.0;
- `bug-fix` 1.0.0;
- `testing` 1.0.0;
- `content-production` 1.0.0;
- `documentation-mirror-import` 1.0.0.

Устаревшие копии из examples удалены, поэтому examples больше не создают
shadowing официальных process ID.

## Data-only граница

Official packs не добавляют ветвлений по software/content/verification в
runtime. Общая логика читает manifests, registry и classifiers; сведения о
profiles, processes, capabilities и classifier markers приходят из YAML.
Политика core hardcode разрешает предметные строки в `packs/official/**`, но
по-прежнему запрещает их в kernel/runtime roots.

Software classifier имеет ID
`processforge.official.software-web.classifier` и загружается только из
активного pack. Проверочный проект с `composer.json` классифицируется как
`software.php-composer` после активации software pack и не получает эту
классификацию без него. Это подтверждает, что classification остаётся
data-driven.

## Discovery и activation

`pack-list --origin official --available` показывает поставляемые official
packs, а `--active` — только активированные в workplace registry.
`process-list --origin official --available` показывает доступные процессы
даже до активации. `process-show software-feature-development` разрешает
официальное определение и сообщает pack metadata. Выполнение неактивного
официального процесса отклоняется с подсказкой `pack-activate`.

`workplace-init --profile generic` создаёт пустой registry official packs.
Профиль `software-development` выбирает pack по данным
`activation.profiles` в manifest и активирует только
`processforge.official.software-development`. После этого
`software-feature-development` разрешён для run/task creation, а capabilities
пакета участвуют в общем capability resolution.

## Production readiness и проверки

В `tools/processforge.py` official packs включены в release inventory,
checksum/public-cleanliness validation и public release smokes. Добавлены
десять специализированных smoke tests для migration, schema, discovery,
kernel boundary, generic/software profiles, classifier activation, minimal
run и отсутствия example shadowing.

Подтверждено:

- Python compilation — PASS;
- schema validation — PASS;
- public cleanliness — PASS;
- десять новых official-pack smokes — PASS;
- прежние domain-neutral-core smokes — PASS;
- прежние capability/specialization/project-override smokes — PASS;
- builtin process catalog doctor: 24 public stable PASS, 0 FAIL;
- checksum write/check — PASS;
- полный `release-test --public --fail-fast --trace-smokes` — PASS
  (`RESULT: PASS`, 463,45 с);
- `release-pack` и проверка состава ZIP — PASS: 777 файлов,
  30 `packs/official/**`, 0 старых `examples/domain-packs/**`, новая schema
  присутствует, manifest содержит 777 файлов;
- полный extracted `release-archive-test` — PASS (`RESULT: PASS`,
  474,77 с);
- `git diff --check` — PASS.

## Ограничения и честные границы

- Шесть knowledge-package manifests внутри software pack пока сохраняют
  `resources: []`: это стабильные catalog identities, но не наполненные
  документационные корпуса.
- В project-local `.agents` нет дополнительного development-flow пакета,
  поэтому работа выполнена по `.pf/AGENTS.md`, `.pf/process-forge.yaml`,
  assignment и существующим ProcessForge CLI/artifacts.
- Assignment capsule самого self-hosted проекта не был создан: его
  capabilities registry не предоставляет требуемые assignment capabilities.
  Это не обходилось waiver-ом. Независимый временный проект с активным
  official software pack успешно прошёл run/task start и capsule creation.
- Независимый implementation review после remediation — PASS. Reviewer
  воспроизвёл pack-aware doctor, custom precedence, knowledge activation,
  workplace/direct-path discovery, public origins и recursive capability union.
- Активные pack manifest и classifier входят в freshness sources. Process и
  knowledge YAML пока не имеют отдельных fingerprint keys; это потенциальное
  последующее усиление freshness diagnostics, а не обнаруженный runtime failure.
