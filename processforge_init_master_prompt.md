# Мастер-промпт: реализация ProcessForge Init

## 0. Роль агента

Ты — архитектор и разработчик подсистемы **ProcessForge Init**.

Твоя задача — спроектировать и реализовать два первичных сценария ProcessForge:

```text
processforge init workplace
processforge init project
```

или их эквиваленты в текущей файловой/скриптовой структуре ProcessForge, если полноценного CLI ещё нет.

ProcessForge — это самостоятельный файловый продукт для формализации повторяемых процессов. Он должен работать без backend/control plane, без базы данных и без обязательного runner’а.

Эта задача НЕ относится к разработке WTAICC. Не проектируй Joomla-компонент, web UI, REST API backend или control plane. Нужно реализовать только файловую инициализацию ProcessForge.

---

# 1. Контекст и границы

## 1.1. Что нужно сделать

Нужно реализовать модель и инструменты для:

1. Инициализации глобального рабочего места / машины.
2. Инициализации конкретного проекта.
3. Автоматического подключения известных глобальных ресурсов к проекту.
4. Безопасного разделения публичных проектных файлов и приватных локальных путей.
5. Проверки корректности настройки через doctor/validate.
6. Подготовки будущего local supervisor/runner mode, но без обязательной реализации runner’а.

## 1.2. Что не нужно делать

Не нужно:

- реализовывать WTAICC;
- реализовывать Joomla backend;
- делать web UI;
- делать package update server;
- делать полноценный marketplace;
- делать runner обязательным;
- хранить секреты;
- писать абсолютные локальные пути в публичные файлы проекта;
- делать проект зависимым от конкретного рабочего места;
- механически копировать старые внутренние файловые структуры;
- упоминать старые внутренние прототипы в публичных файлах ProcessForge.

## 1.3. Источник паттернов

При работе можно изучать существующие внутренние файловые flow-подходы как источник проверенных паттернов:

- глобальные инструкции рабочего места;
- проектные инструкции;
- каскадное подключение знаний;
- платформы;
- инструменты;
- MCP;
- assignments;
- artifacts;
- logs;
- handoffs;
- reviews;
- reusable templates;
- agent boot sequence;
- one-writer-per-file-scope.

Но итоговые публичные файлы ProcessForge не должны содержать упоминаний старых внутренних прототипов.

---

# 2. Главная идея ProcessForge Init

В ProcessForge есть два разных уровня:

```text
1. Workplace Layer
2. Project Flow Layer
```

## 2.1. Workplace Layer

Workplace Layer отвечает на вопрос:

```text
Что доступно на этой машине и где это лежит?
```

Это глобальный слой конкретного устройства:

- компьютер;
- ноутбук;
- сервер;
- CI host;
- runner-machine;
- рабочая машина агента.

Он содержит:

- глобальный `AGENTS.md`;
- `workplace.yaml`;
- словарь терминов;
- реестры платформ;
- реестры папок знаний;
- реестры глобальных шаблонов;
- реестры инструментов;
- реестры MCP;
- локальные политики;
- runtime/cache/logs.

## 2.2. Project Flow Layer

Project Flow Layer отвечает на вопрос:

```text
Как конкретный проект использует ProcessForge на данном рабочем месте?
```

Он содержит:

- `AGENTS.md` проекта;
- публичный `process-forge.yaml`;
- приватный `process-forge.local.yaml`;
- project-local packages;
- project-local templates;
- assignments;
- artifacts;
- contexts;
- logs;
- handoffs;
- reviews;
- ADR;
- runtime.

## 2.3. Ключевое правило

```text
Workplace Init отвечает за “что есть на машине”.
Project Init отвечает за “как этот проект этим пользуется”.
```

---

# 3. Требуемые сценарии

## 3.1. Workplace Init

Сценарий:

```text
processforge init workplace
```

Назначение:

- создать глобальную конфигурацию рабочего места;
- настроить термины и алиасы;
- зарегистрировать платформы;
- зарегистрировать папки знаний;
- зарегистрировать глобальные шаблоны;
- зарегистрировать инструменты;
- зарегистрировать MCP;
- создать machine-readable manifests;
- создать human-readable `AGENTS.md`;
- создать init report;
- выполнить doctor-проверку.

Если полноценного CLI ещё нет, реализуй это как скрипт или набор скриптов в `tools/`, но архитектура должна быть совместима с будущей командой `processforge init workplace`.

## 3.2. Project Init

Сценарий:

```text
processforge init project
```

Назначение:

- подключить конкретный проект к уже настроенному Workplace Layer;
- прочитать `workplace.yaml` и глобальные registry;
- просканировать проект;
- определить тип проекта;
- подобрать платформы;
- подобрать глобальные пакеты знаний;
- подобрать инструменты;
- подобрать MCP;
- подобрать глобальные reusable templates;
- создать project-local ProcessForge structure;
- создать публичный `process-forge.yaml`;
- создать приватный `process-forge.local.yaml`;
- создать project-local `AGENTS.md`;
- создать draft project knowledge package;
- создать initial project artifacts;
- создать project init proposal;
- выполнить doctor-проверку.

Project Init должен работать в режимах:

```text
greenfield
brownfield
```

---

# 4. Обязательные режимы запуска

## 4.1. Human interactive mode

Человек может запустить init и указать параметры вручную.

Даже если интерактивный CLI пока не реализуется, должна быть возможность использовать answers-файл:

```text
workplace-init.answers.yaml
project-init.answers.yaml
```

## 4.2. AI-agent assisted mode

ИИ-агент может выполнить init, но только в безопасном режиме:

```text
proposal-first
dry-run-first
explicit-apply
```

Агент должен:

1. Использовать только пути, переданные пользователем.
2. Не сканировать всю файловую систему.
3. Не сохранять секреты.
4. Не записывать абсолютные локальные пути в публичные файлы.
5. Сначала создать proposal.
6. Не применять изменения без подтверждения, если режим не `--apply`.
7. Создать report о найденных ресурсах и рисках.

---

# 5. Требуемая структура Workplace Layer

Workplace Init должен создавать или обновлять структуру:

```text
<workplace-root>/
├── AGENTS.md
├── workplace.yaml
├── terms.yaml
├── registries/
│   ├── platforms.yaml
│   ├── knowledge-roots.yaml
│   ├── package-roots.yaml
│   ├── templates.yaml
│   ├── tools.yaml
│   └── mcp.yaml
├── cache/
├── runtime/
└── logs/
```

Конкретный путь `<workplace-root>` передаёт пользователь. Не придумывай путь самостоятельно.

---

# 6. Workplace files

## 6.1. AGENTS.md

Глобальный `AGENTS.md` должен быть human-readable entrypoint для агентов на данной машине.

Он должен содержать:

- что это ProcessForge Workplace Layer;
- где находится `workplace.yaml`;
- какие правила действуют на этом устройстве;
- как искать platform contracts;
- как искать knowledge roots;
- как искать tools;
- как искать MCP;
- как искать global templates;
- что запрещено хранить секреты;
- что проектные публичные файлы не должны содержать локальные абсолютные пути;
- что проектные настройки могут переопределять глобальные только по правилам merge policy.

## 6.2. workplace.yaml

Главный machine-readable manifest рабочего места.

Минимальная структура:

```yaml
schema_version: 1

workplace:
  id: "<workplace-id>"
  name: "<human-readable-name>"
  type: workstation
  os: "<windows|linux|macos|server|ci>"
  owner: null

process_forge:
  version_constraint: "^0.1"
  supported_modes:
    - file_only
    - local_supervisor_ready

paths:
  root: "<workplace-root>"
  terms: "terms.yaml"
  registries: "registries"
  cache: "cache"
  runtime: "runtime"
  logs: "logs"

registries:
  platforms: "registries/platforms.yaml"
  knowledge_roots: "registries/knowledge-roots.yaml"
  package_roots: "registries/package-roots.yaml"
  templates: "registries/templates.yaml"
  tools: "registries/tools.yaml"
  mcp: "registries/mcp.yaml"

policies:
  prefer_project_overrides: true
  require_explicit_override_for_locked_policies: true
  shell_is_fallback: true
  do_not_store_secrets: true
  require_public_cleanliness_check: true

capability_resolution:
  missing_required_capability: block
  missing_optional_capability: warn
  prefer_project_tool_over_global: true
  allow_fallback_tools: true
```

## 6.3. terms.yaml

Словарь терминов и алиасов.

Нужен, чтобы пользователь мог говорить привычно:

```text
локальные знания
локальная база знаний
папки со знаниями
глобальные шаблоны
проектные шаблоны
глобальные инструменты
MCP
```

а ProcessForge внутри использовал стабильные machine-readable термины:

```text
knowledge_roots
template_roots
tool_registry
mcp_registry
platform_registry
package_roots
```

Пример:

```yaml
schema_version: 1

terms:
  knowledge_roots:
    label_ru: "папки знаний"
    aliases_ru:
      - "локальные знания"
      - "локальная база знаний"
      - "папки со знаниями"
    definition_ru: >
      Каталоги с документацией, стандартами, справочниками, правилами
      и другими знаниями, доступными на рабочем месте.

  global_templates:
    label_ru: "глобальные шаблоны"
    aliases_ru:
      - "общие шаблоны"
      - "межпроектные шаблоны"
      - "копируемые шаблоны"
    definition_ru: >
      Шаблоны, доступные нескольким проектам на данном рабочем месте.

  project_templates:
    label_ru: "проектные шаблоны"
    aliases_ru:
      - "локальные шаблоны проекта"
    definition_ru: >
      Шаблоны внутри конкретного проекта, имеющие приоритет над глобальными
      шаблонами, если merge policy это разрешает.

  global_tools:
    label_ru: "глобальные инструменты"
    aliases_ru:
      - "сборщики"
      - "линтеры"
      - "генераторы"
      - "утилиты"
    definition_ru: >
      Инструменты, настроенные на рабочем месте и доступные разным проектам.
```

## 6.4. registries/platforms.yaml

Реестр доступных платформ.

Пример:

```yaml
schema_version: 1

platforms:
  - id: joomla
    name: Joomla
    path: "<path-to-platform-package>"
    package_id: "platform.joomla"
    status: available

  - id: php
    name: PHP
    path: "<path-to-platform-package>"
    package_id: "platform.php"
    status: available
```

## 6.5. registries/knowledge-roots.yaml

Реестр физических папок со знаниями.

```yaml
schema_version: 1

knowledge_roots:
  - id: company-knowledge
    label: "Company knowledge"
    path: "<path-to-company-knowledge>"
    scope: organization
    visibility: private
    indexing_policy: allowed

  - id: local-docs
    label: "Local documentation"
    path: "<path-to-local-docs>"
    scope: workplace
    visibility: private
    indexing_policy: allowed

  - id: joomla-docs
    label: "Joomla local docs"
    path: "<path-to-joomla-docs>"
    scope: platform
    platform: joomla
    visibility: private
```

Важно различать:

```text
knowledge root
= физическая папка со знаниями

knowledge package
= версионируемый пакет знаний с manifest
```

## 6.6. registries/package-roots.yaml

Реестр корней с пакетами ProcessForge.

```yaml
schema_version: 1

package_roots:
  - id: global-packages
    label: "Global packages"
    path: "<path-to-global-packages>"
    scope: workplace
    status: available

  - id: organization-packages
    label: "Organization packages"
    path: "<path-to-organization-packages>"
    scope: organization
    status: available
```

## 6.7. registries/templates.yaml

Реестр глобальных reusable templates.

```yaml
schema_version: 1

template_roots:
  - id: global-code-templates
    label: "Global code templates"
    path: "<path-to-global-code-templates>"
    scope: workplace

  - id: global-doc-templates
    label: "Global documentation templates"
    path: "<path-to-global-doc-templates>"
    scope: workplace

template_policy:
  project_templates_override_global: true
  require_template_usage_log: true
  forbid_blind_copy: true
```

## 6.8. registries/tools.yaml

Реестр инструментов как providers capabilities.

```yaml
schema_version: 1

tools:
  - id: phpstan
    name: PHPStan
    capability: php.static_analysis
    scope: global
    command: "<path-or-command>"
    status: configured
    healthcheck:
      command: "<path-or-command> --version"

  - id: package-builder
    name: Package Builder
    capability: package.build
    scope: global
    command: "<path-or-command>"
    status: configured

  - id: media-generator
    name: Media Generator
    capability: media.generate
    scope: global
    command: "<path-or-command>"
    status: optional

  - id: search-api-parser
    name: Search API Parser
    capability: data.parse_from_search_api
    scope: global
    command: "<path-or-command>"
    status: optional
```

Процессы должны требовать capability, а не конкретный tool.

## 6.9. registries/mcp.yaml

Реестр MCP.

```yaml
schema_version: 1

mcp_servers:
  - id: serena
    name: Serena
    capability: repository.symbol_analysis
    status: configured
    transport: stdio
    command: "<command-to-run-serena>"
    auth_ref: null

  - id: context7
    name: Context7
    capability: official_documentation
    status: configured
    transport: stdio
    command: "<command-to-run-context7>"
    auth_ref: null

  - id: browser
    name: Browser MCP
    capability: browser.automation
    status: optional
    transport: stdio
    command: "<command-to-run-browser-mcp>"
    auth_ref: null
```

Секреты не хранить. Только `auth_ref`.

---

# 7. Workplace Init answers file

Для воспроизводимости создать формат:

```text
workplace-init.answers.yaml
```

Пример:

```yaml
schema_version: 1

workplace:
  id: main-workstation
  name: Main Workstation
  type: workstation
  os: windows

paths:
  root: "<processforge-workplace-root>"

  knowledge_roots:
    company: "<path>"
    local_docs: "<path>"

  package_roots:
    global: "<path>"

  template_roots:
    global: "<path>"

  tools_root: "<path>"
  mcp_root: "<path>"

enabled_registries:
  platforms: true
  knowledge_roots: true
  package_roots: true
  templates: true
  tools: true
  mcp: true

policies:
  shell_is_fallback: true
  prefer_symbolic_analysis: true
  require_template_usage_log: true
  do_not_store_secrets: true
```

---

# 8. Project Init

Project Init должен создавать или обновлять проектный слой.

Минимальная структура проекта:

```text
project/
├── AGENTS.md
├── process-forge.yaml
├── process-forge.local.yaml
├── .gitignore
│
├── processes/
├── packages/
├── templates/
├── assignments/
├── artifacts/
├── contexts/
├── logs/
├── handoffs/
├── reviews/
├── adr/
├── schemas/
└── runtime/
```

## 8.1. Публичный process-forge.yaml

Можно коммитить.

Содержит:

- project id;
- project type;
- paths;
- required capabilities;
- optional capabilities;
- selected packages by id/version;
- selected processes;
- selected templates;
- policies;
- ссылку на local config, но не абсолютный путь.

Пример:

```yaml
schema_version: 1

process_forge:
  version: "0.1.0"
  mode: file_only

project:
  id: example-project
  name: Example Project
  type: software_project

workplace:
  reference: local_file
  local_config: process-forge.local.yaml

detected:
  languages:
    - php
    - javascript

  platforms:
    - joomla

  project_kind:
    - joomla_extension

paths:
  processes: processes
  packages: packages
  templates: templates
  assignments: assignments
  artifacts: artifacts
  contexts: contexts
  logs: logs
  handoffs: handoffs
  reviews: reviews
  adr: adr
  schemas: schemas
  runtime: runtime

knowledge_stack:
  - package: processforge.core
    version: "^0.1"

  - package: direction.software-development
    version: "^1.0"
    source: workplace

  - package: platform.joomla
    version: "^1.0"
    source: workplace

  - package: toolchain.php
    version: "^1.0"
    source: workplace

  - package: project.example-project
    version: "0.1.0"
    source: project

required_capabilities:
  - repository.read
  - markdown.editing
  - php

optional_capabilities:
  - repository.symbol_analysis
  - official_documentation
  - php.static_analysis
  - php.unit_testing

policies:
  one_writer_per_file_scope: true
  approved_artifacts_are_protected: true
  execution_context_is_immutable: true
  public_files_must_not_contain_local_absolute_paths: true
```

## 8.2. Приватный process-forge.local.yaml

Не коммитить.

Содержит:

- абсолютный путь к `workplace.yaml`;
- локальный project root;
- private package roots;
- private template roots;
- local runtime settings;
- local tool preferences.

Пример:

```yaml
schema_version: 1

workplace:
  manifest: "<absolute-path-to-workplace.yaml>"

local:
  project_root: "<absolute-path-to-project>"

overrides:
  package_roots:
    - "<absolute-path-to-private-project-packages>"

  template_roots:
    - "<absolute-path-to-private-project-templates>"

  tool_preferences:
    repository.symbol_analysis: serena
    php.static_analysis: phpstan

runtime:
  mode: manual
  queue: runtime/queue
  events: runtime/events
```

## 8.3. .gitignore

Project Init обязан добавить или предложить добавить:

```gitignore
process-forge.local.yaml
runtime/
cache/
private-notes/
.secrets/
*.tmp
*.bak
```

Если есть local runner:

```gitignore
runtime/queue/running/
runtime/agents/
runtime/*.pid
```

---

# 9. Project Init behavior

## 9.1. Общая схема

```text
project init scan
  ↓
project init proposal
  ↓
review / approve
  ↓
project init apply
  ↓
doctor project
```

## 9.2. Greenfield mode

Если проект новый или пустой:

- создать структуру;
- создать `AGENTS.md`;
- создать `process-forge.yaml`;
- создать `process-forge.local.yaml`;
- создать starter project package;
- предложить starter processes;
- предложить starter assignments;
- предложить starter templates.

## 9.3. Brownfield mode

Если проект уже существует:

- не перезаписывать существующие файлы без approval;
- просканировать проект;
- создать reports;
- создать proposal;
- пометить выводы как draft/observed;
- создать `process-forge.yaml`;
- создать `process-forge.local.yaml`;
- создать project package draft;
- обновить `.gitignore`;
- создать review.

Правило:

```text
no overwrite without explicit approval
```

---

# 10. Project detection

Project Init должен автоматически определить проектную специфику.

## 10.1. Эвристики

Примеры:

```text
composer.json                     → PHP project
package.json                      → Node/frontend project
phpunit.xml                       → PHPUnit tests
*.xml Joomla manifest             → Joomla extension
administrator/components/*        → Joomla component
plugins/*                         → Joomla plugins
media/*                           → media assets
.github/workflows/*               → CI workflows
README.md                         → documentation entry
docs/*                            → documentation layer
content/*                         → content project candidate
```

## 10.2. Classification report

Создать:

```text
artifacts/project-classification-report.md
```

Содержит:

- detected languages;
- detected platforms;
- detected frameworks;
- detected project type;
- confidence;
- evidence;
- unknowns.

## 10.3. Repository map

Создать:

```text
artifacts/repository-map.md
```

Содержит:

- основные директории;
- где код;
- где docs;
- где tests;
- где assets;
- где build/package config;
- какие файлы критичны;
- какие зоны нельзя менять без review.

## 10.4. Project conventions

Создать:

```text
artifacts/project-conventions.md
```

Содержит:

- observed conventions;
- confirmed conventions;
- unknown conventions;
- naming;
- coding style;
- testing style;
- docs style;
- packaging style.

Важно: найденные выводы не считать утверждёнными автоматически.

Использовать статусы:

```text
observed
confirmed
unknown
```

---

# 11. Global resource matching

Project Init должен автоматически сопоставить проект с известными глобальными ресурсами рабочего места.

## 11.1. Matching sources

Использовать:

- `workplace.yaml`;
- `registries/platforms.yaml`;
- `registries/knowledge-roots.yaml`;
- `registries/package-roots.yaml`;
- `registries/templates.yaml`;
- `registries/tools.yaml`;
- `registries/mcp.yaml`;
- project scan results;
- user answers.

## 11.2. Matching output

Создать:

```text
artifacts/global-resource-matching-report.md
```

Содержит:

- matched platforms;
- matched packages;
- matched tools;
- matched MCP;
- matched templates;
- missing required capabilities;
- optional missing capabilities;
- conflicts;
- recommendations.

---

# 12. Project-specific package

Project Init должен создать draft project package:

```text
packages/project.<project-id>.yaml
```

Пример:

```yaml
id: project.example-project
name: Example Project Knowledge
version: 0.1.0
scope: project
status: draft

project:
  id: example-project

provides:
  capabilities:
    - project.example-project.context

content:
  references:
    - artifacts/project-profile.md
    - artifacts/repository-map.md
    - artifacts/project-conventions.md
    - artifacts/toolchain-detection-report.md
    - artifacts/template-matching-report.md

policies:
  file_ownership:
    default: one_writer_per_scope

  public_cleanliness:
    forbid_absolute_local_paths: true
```

Этот пакет должен содержать только проектную специфику.

---

# 13. Project Init artifacts

Project Init должен создать или предложить создать:

```text
artifacts/project-profile.md
artifacts/repository-map.md
artifacts/project-conventions.md
artifacts/toolchain-detection-report.md
artifacts/mcp-capability-report.md
artifacts/template-matching-report.md
artifacts/global-resource-matching-report.md
artifacts/project-init-proposal.md
reviews/project-init-review.md
```

## 13.1. Project profile

Содержит:

- название;
- тип проекта;
- назначение;
- платформы;
- языки;
- основные директории;
- публичные зоны;
- приватные зоны;
- предполагаемые процессы;
- ограничения.

## 13.2. Toolchain detection report

Содержит:

- найденные project-local tools;
- доступные global tools;
- missing tools;
- required capabilities;
- optional capabilities;
- fallback mapping.

## 13.3. MCP capability report

Содержит:

- доступные MCP на workplace;
- полезные MCP для проекта;
- required/optional;
- missing MCP;
- рекомендации.

## 13.4. Template matching report

Содержит:

- подходящие global templates;
- найденные project templates;
- suggested templates;
- templates requiring adaptation;
- templates not safe to use.

---

# 14. Project-local AGENTS.md

Project Init должен создать `AGENTS.md`:

```markdown
# Project Agent Instructions

This project uses ProcessForge.

## Start here

1. Read `process-forge.yaml`.
2. Load local configuration from `process-forge.local.yaml` if available.
3. Resolve the workplace layer.
4. Use assignments from `assignments/`.
5. Write logs to `logs/`.
6. Save artifacts to `artifacts/`.
7. Write handoffs to `handoffs/`.
8. Request reviews in `reviews/`.

## Important rules

- Do not edit files outside assignment scope.
- Do not put absolute local paths into public files.
- Do not commit private local config.
- Use project-local templates before global templates when allowed.
- Record template usage.
```

---

# 15. Doctor commands

Нужны проверки после init.

Если полноценного CLI пока нет, реализовать как scripts.

## 15.1. doctor workplace

Будущий CLI:

```text
processforge doctor workplace
```

Проверяет:

- есть ли `workplace.yaml`;
- валиден ли `workplace.yaml`;
- есть ли registry files;
- существуют ли пути;
- читаются ли package roots;
- читаются ли knowledge roots;
- доступны ли tools;
- отвечают ли MCP, если healthcheck возможен;
- нет ли секретов;
- нет ли явно опасных абсолютных путей в публичных шаблонах;
- все ли required capabilities имеют providers.

## 15.2. doctor project

Будущий CLI:

```text
processforge doctor project
```

Проверяет:

- есть ли `process-forge.yaml`;
- валиден ли `process-forge.yaml`;
- есть ли `process-forge.local.yaml`, если required;
- `process-forge.local.yaml` есть в `.gitignore`;
- публичный manifest не содержит абсолютных локальных путей;
- workplace manifest доступен;
- required capabilities resolved;
- selected packages exist;
- selected templates exist;
- project package существует;
- init artifacts существуют;
- reviews созданы.

## 15.3. Result format

Вывод:

```text
PASS
WARN
FAIL
```

Пример:

```text
PASS: workplace.yaml found
PASS: knowledge root company-knowledge exists
WARN: optional MCP browser is not configured
FAIL: required capability repository.symbol_analysis has no provider
```

---

# 16. Required schemas

Добавить или обновить schemas:

```text
schemas/workplace.schema.json
schemas/terms.schema.json
schemas/platform-registry.schema.json
schemas/knowledge-roots-registry.schema.json
schemas/package-roots-registry.schema.json
schemas/template-registry.schema.json
schemas/tool-registry.schema.json
schemas/mcp-registry.schema.json
schemas/workplace-init-answers.schema.json
schemas/project-init-answers.schema.json
schemas/process-forge-manifest.schema.json
```

Если времени мало, сначала сделать минимальные schemas, но они должны проверять хотя бы:

- required fields;
- schema_version;
- ids;
- paths;
- status values;
- capability values as strings;
- отсутствие secrets fields;
- отсутствие абсолютных путей в публичном project manifest.

---

# 17. Required templates

Добавить templates:

```text
templates/workplace.yaml
templates/terms.yaml
templates/registries/platforms.yaml
templates/registries/knowledge-roots.yaml
templates/registries/package-roots.yaml
templates/registries/templates.yaml
templates/registries/tools.yaml
templates/registries/mcp.yaml
templates/workplace-init.answers.yaml
templates/project-init.answers.yaml
templates/process-forge.yaml
templates/process-forge.local.yaml
templates/project-agents-template.md
templates/project-init-proposal-template.md
templates/project-profile-template.md
templates/repository-map-template.md
templates/project-conventions-template.md
templates/global-resource-matching-report-template.md
templates/project-init-review-template.md
```

---

# 18. Required docs

Добавить docs:

```text
docs/concepts/workplace-init.md
docs/concepts/project-init.md
docs/concepts/workplace-layer.md
docs/concepts/project-flow-layer.md
docs/concepts/capability-resolution.md
docs/concepts/public-private-config.md
docs/authoring/workplace-configuration.md
docs/authoring/project-initialization.md
docs/validation/doctor-workplace.md
docs/validation/doctor-project.md
```

---

# 19. Required process definitions

Добавить seed process:

```text
processes/workplace-initialization.yaml
processes/project-initialization.yaml
```

## 19.1. workplace-initialization stages

```text
intake
terms setup
registry setup
tool discovery
mcp discovery
proposal
review
apply
doctor
```

## 19.2. project-initialization stages

```text
intake
workplace resolution
repository scan
project classification
global resource matching
project specificity extraction
proposal
review
apply
doctor
```

---

# 20. Required tooling MVP

Если в текущем ProcessForge уже есть tools, расширь их.

Минимально реализовать:

```text
tools/processforge_init.py
tools/doctor_workplace.py
tools/doctor_project.py
```

или единый entrypoint:

```text
tools/processforge.py
```

с командами:

```text
init-workplace
doctor-workplace
init-project
doctor-project
```

## 20.1. Минимальные команды

Пример CLI:

```text
python tools/processforge.py init-workplace --root <workplace-root> --answers <answers.yaml> --dry-run
python tools/processforge.py init-workplace --root <workplace-root> --answers <answers.yaml> --apply

python tools/processforge.py doctor-workplace --root <workplace-root>

python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --answers <answers.yaml> --dry-run
python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --answers <answers.yaml> --apply

python tools/processforge.py doctor-project --project-root <project-root>
```

## 20.2. Dependency policy

Используй текущий стек ProcessForge.

Если стек не определён:

- предпочитай Python;
- держи зависимости минимальными;
- если нужен YAML parser, явно задокументируй dependency;
- не требуй тяжёлых framework’ов;
- поддерживай Windows paths и POSIX paths;
- не хардкодь пользовательские локальные пути.

---

# 21. Safety rules

## 21.1. No secrets

Init не должен сохранять:

- API keys;
- passwords;
- tokens;
- private SSH keys;
- cookies.

Допустимо:

```text
auth_ref
credential_ref
secret_ref
```

## 21.2. Public/private separation

Публичные файлы не должны содержать:

- локальные абсолютные пути;
- имена приватных машин;
- секреты;
- внутренние scratch notes;
- приватные knowledge paths.

Приватные файлы:

```text
process-forge.local.yaml
private-notes/**
runtime/**
cache/**
.secrets/**
```

должны быть в `.gitignore`.

## 21.3. No overwrite without approval

В brownfield-проекте Project Init не должен перезаписывать существующие файлы без явного approval.

Поведение:

```text
if file exists:
  create .candidate
  or report conflict
  or require --force/--approve-overwrite
```

## 21.4. Agent-assisted init safety

ИИ-агент в init режиме должен:

- сначала создать proposal;
- указать, что будет создано/изменено;
- указать риски;
- указать найденные пути;
- указать missing capabilities;
- не применять изменения без apply mode.

---

# 22. Validation and tests

Реализуй или опиши тестовые сценарии.

## 22.1. Workplace Init tests

Проверить:

1. Empty workplace root creates expected files.
2. Re-running init is idempotent.
3. Missing required answers produce clear error.
4. Terms file validates.
5. Registries validate.
6. Doctor passes for valid workplace.
7. Doctor warns for optional missing MCP.
8. Doctor fails for missing required capability provider.
9. No secrets stored.
10. Windows-like and POSIX-like paths are handled.

## 22.2. Project Init tests

Проверить:

1. Greenfield project creates expected structure.
2. Brownfield project does not overwrite files.
3. `.gitignore` includes private local files.
4. Public `process-forge.yaml` contains no absolute local paths.
5. `process-forge.local.yaml` contains workplace path.
6. Project classification creates report.
7. Global resource matching creates report.
8. Project package draft is created.
9. Required capabilities are resolved or reported.
10. Doctor project passes for valid project.
11. Doctor project fails when workplace manifest is missing.
12. Joomla/PHP/content/testing examples classify reasonably if fixtures exist.

## 22.3. Public cleanliness

Добавить проверку:

- публичные files do not contain forbidden private path patterns;
- public files do not contain secrets-like keys;
- public files do not contain internal prototype names, if forbidden by release policy.

---

# 23. Agent work decomposition

Если задача большая, оркестратор должен разделить работу.

## Agent A — Init Architecture

Ответственность:

- workplace init concept;
- project init concept;
- public/private separation;
- mode model.

Files:

```text
docs/concepts/workplace-init.md
docs/concepts/project-init.md
docs/concepts/public-private-config.md
adr/*
```

## Agent B — Schemas

Ответственность:

- workplace schema;
- terms schema;
- registries schemas;
- init answers schemas;
- process-forge manifest updates.

Files:

```text
schemas/**
```

## Agent C — Templates

Ответственность:

- workplace templates;
- registries templates;
- project templates;
- reports templates.

Files:

```text
templates/**
```

## Agent D — CLI / Tools

Ответственность:

- init workplace tool;
- init project tool;
- doctor workplace;
- doctor project;
- dry-run/apply behavior.

Files:

```text
tools/**
```

## Agent E — Project Detection

Ответственность:

- project scan;
- classification heuristics;
- resource matching;
- report generation.

Files:

```text
tools/**
docs/concepts/project-init.md
templates/*report*
```

## Agent F — Docs and Examples

Ответственность:

- getting started;
- init guide;
- examples;
- greenfield/brownfield examples.

Files:

```text
docs/**
examples/**
```

## Agent G — QA / Review

Ответственность:

- test plan;
- public cleanliness review;
- schema consistency;
- CLI behavior review.

Files:

```text
reviews/**
artifacts/validation-report.md
```

Правило:

```text
Один writer на область файлов.
```

Не допускай, чтобы несколько агентов одновременно меняли одни и те же schemas/tools/templates.

---

# 24. Deliverables

По итогам работы должны быть:

## 24.1. Документация

```text
docs/concepts/workplace-init.md
docs/concepts/project-init.md
docs/concepts/public-private-config.md
docs/concepts/capability-resolution.md
docs/validation/doctor-workplace.md
docs/validation/doctor-project.md
```

## 24.2. Схемы

```text
schemas/workplace.schema.json
schemas/terms.schema.json
schemas/platform-registry.schema.json
schemas/knowledge-roots-registry.schema.json
schemas/package-roots-registry.schema.json
schemas/template-registry.schema.json
schemas/tool-registry.schema.json
schemas/mcp-registry.schema.json
schemas/workplace-init-answers.schema.json
schemas/project-init-answers.schema.json
```

## 24.3. Шаблоны

```text
templates/workplace.yaml
templates/terms.yaml
templates/registries/*.yaml
templates/workplace-init.answers.yaml
templates/project-init.answers.yaml
templates/process-forge.yaml
templates/process-forge.local.yaml
templates/project-agents-template.md
templates/project-init-proposal-template.md
templates/project-profile-template.md
templates/repository-map-template.md
templates/project-conventions-template.md
templates/global-resource-matching-report-template.md
templates/project-init-review-template.md
```

## 24.4. Инструменты

```text
tools/processforge.py
```

или эквивалентные scripts:

```text
tools/init_workplace.py
tools/init_project.py
tools/doctor_workplace.py
tools/doctor_project.py
```

## 24.5. Процессы

```text
processes/workplace-initialization.yaml
processes/project-initialization.yaml
```

## 24.6. Reports

После собственной проверки создать:

```text
artifacts/init-implementation-report.md
artifacts/validation-report.md
reviews/init-implementation-review.md
```

---

# 25. Acceptance criteria

Работа считается выполненной, если:

1. Есть формальная модель Workplace Init.
2. Есть формальная модель Project Init.
3. Есть шаблоны `workplace.yaml` и `process-forge.yaml`.
4. Есть разделение public/private config.
5. Есть `process-forge.local.yaml`.
6. Есть `.gitignore` policy.
7. Есть terms/aliases model.
8. Есть registries для platforms, knowledge roots, package roots, templates, tools, MCP.
9. Есть answers files.
10. Есть doctor workplace.
11. Есть doctor project.
12. Есть dry-run/proposal-first режим.
13. Есть apply режим.
14. Есть greenfield project init.
15. Есть brownfield project init без перезаписи файлов.
16. Есть project scan/classification report.
17. Есть global resource matching report.
18. Есть project package draft.
19. Есть public cleanliness validation.
20. Нет зависимости от WTAICC.
21. Нет обязательной зависимости от runner.
22. Нет секретов в generated manifests.
23. Нет абсолютных локальных путей в публичном `process-forge.yaml`.
24. Документация объясняет сценарии человеку и ИИ-агенту.

---

# 26. Финальная инструкция

Начни с инспекции текущего ProcessForge-репозитория.

Не ломай существующую структуру, если она уже создана. Встраивай init-модель в текущую архитектуру ProcessForge.

Сначала создай/обнови спецификацию и templates.

Затем реализуй минимальный tooling.

Затем добавь doctor-проверки.

Затем добавь examples и validation reports.

При любой неопределённости:

```text
- не хардкодь пути;
- не сохраняй секреты;
- не пиши локальные пути в публичные файлы;
- используй proposal-first;
- не перезаписывай brownfield-файлы без approval;
- отделяй workplace layer от project layer;
- отделяй physical roots от versioned packages;
- отделяй tools от reusable templates.
```

Главная цель:

> ProcessForge Init должен сделать сложную каскадную систему пригодной к первому использованию: сначала настроить рабочее место, затем подключить конкретный проект к известным глобальным знаниям, инструментам, MCP и шаблонам, не нарушая публичность проекта и воспроизводимость flow.
