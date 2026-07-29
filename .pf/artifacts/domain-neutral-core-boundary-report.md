# Отчёт: предметно-нейтральная граница ядра

Дата: 2026-07-29
Задание: `задания/processforge_domain_neutral_core_boundary_master_prompt.md`
Статус: выполнено

## Результат

ProcessForge core теперь содержит только artifact-driven механику: процессы,
задания, runs/tasks/iterations, контекст, capability resolution, оркестрацию,
supervision, authoring, resource management и release assurance. Предметная
область проекта не определяется встроенным списком технологий или имён файлов.

Пустое рабочее место создаётся без domain knowledge packages, domain
capabilities, domain processes и активных project classifiers.

## Переносы

Из core/default surface перенесены с сохранением process ids:

- `software-feature-development` и `bug-fix` в
  `examples/domain-packs/software-web/`;
- `content-production` и `documentation-mirror-import` в
  `examples/domain-packs/content-workflow/`;
- `testing` в `examples/domain-packs/verification-workflow/`;
- `docs.php` и пять `docs.web.*` seeds в optional `software-web` example pack.

Каждый pack имеет собственный `package.yaml`, README, процессы и prompts,
помечен `optional_example`, `core: false`, `installed_by_default: false`.
Наличие pack в дистрибутиве не включает его в каталог и не активирует ресурсы.

Универсальные процессы `multi-agent-task-orchestration`,
`runtime-driver-registry`, `process-supervisor` и экспериментальный
`orchestrator-shell-agents-supervision` принадлежат `process-forge-core` и не
зависят от software/testing packages.

## Классификация

Добавлены:

- `schemas/project-classifier.schema.json`;
- `schemas/project-classifier-registry.schema.json`;
- `templates/project-classifier.yaml`;
- пустой `templates/registries/project-classifiers.yaml`;
- workplace/project registries и example classifier в `software-web`.

Runtime загружает только явно активные classifier entries, применяет
универсальные `exists`/`all`/`any` rules и возвращает `unclassified`/`unknown`,
если правил нет или они не совпали. `composer.json`, `package.json`,
`pyproject.toml`, `.github/workflows` и расширения исходников сами по себе
ничего не классифицируют.

Результат классификации сохраняется в project-context snapshot и capsule.
Изменение marker-файла или результата классификации делает snapshot stale.
Project classifier definitions в стандартном `.pf/project-classifiers/`
участвуют в source fingerprints.

## Защита границы

- `policies/core-hardcode-policy.yaml` проверяет runtime, CLI, schemas,
  templates, core processes/prompts/packages и seeds, включая glob targets.
- Schema validator теперь проверяет `oneOf`, `minProperties` и `uniqueItems`.
- Public cleanliness и checksum inventory включают `policies/` и `seeds/`.
- Добавлены и включены в public release-test девять обязательных
  domain-neutral smokes.
- Прежние lifecycle-тесты сохранены как regression checks optional domain
  packs; core tests используют нейтральные fixture process ids.
- EN/RU документация описывает core boundary, classifiers и process catalog
  boundary.

## Проверки

- schema validation: PASS;
- public cleanliness: PASS;
- checksum write/check: PASS;
- public `release-test`: PASS, 128/128 checks, 541.148 s;
- `release-pack`: PASS, `dist/processforge.zip`, 762 files;
- full `release-archive-test`: PASS, hashes/manifest/root совпадают,
  extracted public release-test PASS, 531.57 s;
- ZIP inspection: domain seeds и domain core processes отсутствуют в default
  paths; три optional packs и classifier schemas присутствуют;
- `git diff --check`: PASS.

## Процессные доказательства

Выполнены три независимых read-only аудита:

- boundary/catalog: найден implicit default indexing seeds и domain ownership
  core processes/packages;
- classifier/runtime: найден stale-context gap при изменении классификации;
- release/assurance: найдены обязательные validator/release registrations и
  старые smoke fixtures.

Capsule для `.pf/assignments/task-001-domain-neutral-core-boundary.yaml` не был
создан: после refresh resolver всё ещё не нашёл объявленные capability ids
`repository_read`, `markdown_editing`, `schema_validation` в подключённом
workplace registry. Продуктовые и release проверки не пропущены; waiver не
использовался.

## Остаточные улучшения

Не блокируют текущую domain-neutral границу:

- добавить отдельный doctor diagnostic для missing/malformed active classifier;
- определить scope precedence и shadowing diagnostic для duplicate classifier
  ids;
- добавить операторскую CLI-команду import/register classifier;
- fingerprint arbitrary external classifier paths независимо от изменения
  результата классификации.
