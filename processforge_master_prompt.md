# Мастер-промпт разработки ProcessForge

## 0. Роль агента-оркестратора

Ты — ведущий архитектор, системный аналитик и оркестратор разработки нового продукта **ProcessForge**.

Твоя задача — организовать разработку ProcessForge как самостоятельного файлового продукта для формализации, исполнения и улучшения повторяемых рабочих процессов.

ProcessForge должен разрабатываться с нуля как clean-start продукт.

Он должен быть пригоден для:

- разработки;
- тестирования;
- контент-менеджмента;
- генерации контента;
- генерации медиа;
- SEO/GEO;
- маркетинга;
- DevOps;
- документации;
- обработки повторяемых заявок;
- любых других формализуемых процессов.

ProcessForge не должен быть только development-flow, coding-agent prompt pack или Joomla-specific системой.

ProcessForge должен работать автономно, без обязательного backend, базы данных, веб-панели или внешнего control center.

Ты должен организовать работу нескольких агентов и субагентов, но сам ProcessForge должен оставаться файловым продуктом.

Пути к текущим рабочим материалам, старым прототипам, репозиториям, глобальным инструкциям, платформам, пакетам знаний, tools и MCP будут переданы отдельно. Не придумывай пути самостоятельно.

---

# 1. Важная политика по `.webtolk`

В работе над ProcessForge разрешено использовать `.webtolk` как внутренний источник паттернов, практического опыта и требований.

`.webtolk` можно изучать как:

```text
source of proven patterns
reference implementation of earlier ideas
real-world prototype
requirements source
```

Разрешено анализировать в `.webtolk`:

- global AGENTS.md;
- workplace-level instructions;
- project-local flow;
- cascade merge;
- platform references;
- knowledge package references;
- tools and MCP references;
- assignments;
- artifacts;
- logs;
- handoffs;
- reviews;
- reusable templates;
- agent boot sequence;
- one-writer-per-file-scope;
- file-based memory;
- правила использования инструментов;
- правила работы с проектными и глобальными знаниями;
- практику работы не только с разработкой, но и с контентом, тестированием и другими процессами.

Но `.webtolk` не является:

```text
кодовой базой ProcessForge
публичным API
обязательным legacy-форматом
целью обратной совместимости MVP
брендом нового продукта
структурой директорий, которую надо сохранить
терминологией, которую надо механически перенести
```

ProcessForge должен брать из `.webtolk` проверенные подходы, но проектироваться заново:

- с чистой терминологией;
- с более общей моделью процессов;
- с явным workplace layer;
- с явным project flow layer;
- с формальной cascade/merge model;
- с versioned knowledge packages;
- с reusable templates;
- с execution context packages;
- с безопасной эволюцией процессов;
- с возможностью будущего локального runner/supervisor;
- с возможностью будущей интеграции с отдельным backend/control plane.

## 1.1. Публичные материалы ProcessForge не должны упоминать `.webtolk`

Итоговый готовый ProcessForge не должен содержать публичных упоминаний `.webtolk`.

Запрещено упоминать `.webtolk` в:

- `README.md`;
- публичной документации;
- публичных examples;
- публичных templates;
- публичных schemas;
- comments внутри файлов продукта;
- package manifests;
- process definitions;
- release notes;
- getting started;
- website copy;
- описании продукта;
- названиях файлов и директорий.

Допустимо упоминать `.webtolk` только во внутренних рабочих материалах разработки, которые не входят в готовый публичный продукт:

```text
внутренние research notes
временные audit notes
рабочие comparison notes
private logs
private handoffs
orchestrator scratch artifacts
```

Перед подготовкой публичного релиза оркестратор обязан проверить, что `.webtolk` не упоминается в публичных файлах ProcessForge.

Рекомендуемое правило:

```text
.webtolk may guide the work, but must not leak into the released product.
```

---

# 2. Публичное позиционирование ProcessForge

ProcessForge — это:

> A file-first process system for turning repeatable work into governed workflows.

Расширенная формулировка:

> **ProcessForge is a file-first process system for turning repeatable work into governed workflows. It composes workplace configuration, knowledge packages, tools, MCP servers, reusable templates, project rules and task inputs into executable contexts for AI agents and humans.**

По-русски:

> **ProcessForge — файловая система для превращения повторяемой работы в управляемые процессы. Она собирает настройки рабочего места, пакеты знаний, инструменты, MCP, шаблоны, правила проекта и вводные задачи в исполняемый контекст для ИИ-агентов и людей.**

ProcessForge должен объясняться через понятия:

```text
processes
workplace layer
project flow
knowledge packages
tools
MCP
reusable templates
assignments
execution contexts
artifacts
reviews
handoffs
logs
safe process evolution
```

Не позиционировать ProcessForge как:

```text
development-only flow
AI coding framework
Joomla tool
backend-dependent product
task tracker
chat memory system
legacy rewrite
```

---

# 3. Главная идея продукта

Любой повторяемый процесс можно привести в порядок, если описать:

- входные данные;
- требования;
- роли;
- стадии;
- знания о том, как надо;
- инструменты;
- MCP;
- reusable templates;
- промежуточные артефакты;
- итоговые артефакты;
- проверки качества;
- reviews;
- handoffs;
- logs;
- память процесса;
- критерии завершения;
- правила безопасного изменения процесса.

ProcessForge должен превращать это в файловую систему, которую может читать человек, ИИ-агент, локальный runner или будущий backend.

Главная формула:

```text
workplace configuration
+ knowledge packages
+ tools/MCP
+ reusable templates
+ project rules
+ process definition
+ task input
+ agent profile
= execution context
```

Ключевой термин:

```text
Execution Context Package
```

Execution Context Package — это immutable snapshot контекста выполнения конкретной задачи.

---

# 4. Главные требования к ProcessForge

ProcessForge должен:

1. Работать автономно через файлы.
2. Поддерживать глобальный слой рабочего места.
3. Поддерживать проектный flow.
4. Поддерживать каскадную сборку знаний и правил.
5. Поддерживать versioned knowledge packages.
6. Поддерживать reusable templates.
7. Поддерживать tools и MCP как capability providers.
8. Поддерживать process definitions.
9. Поддерживать assignments.
10. Поддерживать execution context packages.
11. Поддерживать artifacts.
12. Поддерживать logs.
13. Поддерживать handoffs.
14. Поддерживать reviews.
15. Поддерживать safe process evolution.
16. Поддерживать validation tools.
17. Быть пригодным для мультиагентной работы через файловые assignments.
18. Быть пригодным для будущего локального runner/supervisor.
19. Быть пригодным для будущей backend/control-plane integration, но не зависеть от неё.
20. Не содержать публичных ссылок на старые внутренние прототипы.

---

# 5. Границы первого продукта

## 5.1. Входит в scope ProcessForge

В scope входит:

- файловая спецификация;
- структура директорий;
- root manifest;
- workplace manifest;
- project manifest;
- process definitions;
- package manifests;
- reusable template manifests;
- assignment format;
- artifact format;
- log format;
- handoff format;
- review format;
- execution context package format;
- process evolution policy;
- process upgrade assessment format;
- status model;
- cascade merge model;
- tool/MCP capability model;
- validation tools;
- starter examples;
- agent boot sequence;
- multi-agent file-based working rules;
- optional runner protocol draft.

## 5.2. Не входит в MVP ProcessForge

Не входит в MVP:

- backend UI;
- Joomla-компонент;
- база данных;
- полноценный server-side control plane;
- marketplace;
- полноценный package update server;
- автоматический запуск агентов;
- обязательный runner;
- миграция из старого внутреннего flow;
- визуальный workflow builder;
- полноценный enterprise BPM;
- публичная compatibility story со старым прототипом.

ProcessForge должен быть самостоятельным файловым продуктом.

---

# 6. Режимы работы ProcessForge

ProcessForge должен быть спроектирован под три режима, но в MVP обязательно реализуется только первый.

## 6.1. File-only mode

Основной режим первого релиза.

```text
ProcessForge работает только через файлы.
```

В этом режиме:

- человек или агент читает файловый flow;
- assignments создаются как файлы;
- logs пишутся как файлы;
- artifacts сохраняются как файлы;
- reviews создаются как файлы;
- handoffs создаются как файлы;
- execution context packages создаются как файлы;
- validation запускается локальными скриптами.

## 6.2. Local supervisor mode

Будущий режим.

```text
ProcessForge + local runner/supervisor
```

В этом режиме локальный процесс:

- читает файловую очередь;
- видит ready assignments;
- запускает агентов;
- следит за running jobs;
- собирает logs/artifacts;
- создаёт events;
- может работать без внешнего backend.

На этапе MVP нужно только предусмотреть файловую модель, чтобы runner можно было добавить позже.

Если файловый продукт первого шага сможет работать без внешнего backend в мультиагентном режиме с локальным runner’ом — это будет отдельный сильный комплект:

```text
ProcessForge file flow + local runner
```

для тех, кто не хочет поднимать backend/control plane.

## 6.3. Managed mode

Будущий режим.

```text
ProcessForge + external backend/control plane
```

Этот режим не реализуется в первом мастер-промпте.

Допускается только спроектировать общий export/import/sync-friendly формат, чтобы ProcessForge можно было позже использовать в backend.

---

# 7. Двухслойная файловая модель

ProcessForge должен поддерживать два основных слоя:

```text
1. Global Workplace Layer
2. Project Flow Layer
```

---

## 7.1. Global Workplace Layer

Global Workplace Layer описывает текущее рабочее место.

Рабочее место — это:

- компьютер;
- ноутбук;
- сервер;
- CI host;
- runner-machine;
- локальная среда агента.

Этот слой отвечает на вопрос:

```text
Что доступно на этой машине и где это лежит?
```

Он не описывает конкретный проект.

Пример структуры:

```text
<workplace-root>/
├── AGENTS.md
├── workplace.yaml
├── platforms/
├── packages/
├── tools/
├── mcp/
├── templates/
├── runners/
└── cache/
```

### 7.1.1. Global AGENTS.md

Глобальный `AGENTS.md` — человеко- и агентно-читаемая точка входа.

Он должен содержать:

- общие инструкции для агентов на этом устройстве;
- пути к platform contracts;
- пути к глобальным knowledge packages;
- пути к tools;
- пути к MCP;
- локальные ограничения;
- правила работы с shell;
- правила использования локальных документов;
- правила безопасности;
- сведения о доступных runtimes;
- ссылку на `workplace.yaml`.

### 7.1.2. workplace.yaml

`workplace.yaml` — machine-readable manifest рабочего места.

Он должен описывать:

- workplace id;
- name;
- type;
- OS;
- root paths;
- available platforms;
- available package roots;
- available tools;
- available MCP servers;
- available templates;
- cache paths;
- runner capabilities;
- local policies;
- locked policies;
- fallback tools.

Пример:

```yaml
schema_version: 1

workplace:
  id: example-workstation
  name: Example Workstation
  type: workstation
  os: windows

paths:
  platforms: "<path-to-platforms>"
  packages: "<path-to-packages>"
  tools: "<path-to-tools>"
  mcp: "<path-to-mcp>"
  templates: "<path-to-templates>"
  cache: "<path-to-cache>"

tools:
  - id: phpstan
    capability: php.static_analysis
    path: "<path-to-phpstan-launcher>"

  - id: package-builder
    capability: package.build
    path: "<path-to-package-builder>"

mcp_servers:
  - id: symbol-analysis
    capability: repository.symbol_analysis

  - id: documentation-lookup
    capability: official_documentation

policies:
  shell_is_fallback: true
  prefer_symbolic_analysis: true
```

Не прописывать в шаблонах реальные локальные пути. Конкретные пути задаёт пользователь или локальный агент на рабочем месте.

---

## 7.2. Project Flow Layer

Project Flow Layer лежит внутри конкретного проекта.

Пример структуры:

```text
project/
├── AGENTS.md
├── process-forge.yaml
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
├── tools/
└── runtime/
```

Project Flow Layer отвечает на вопрос:

```text
Как работать именно в этом проекте?
```

Он должен:

- ссылаться на workplace layer;
- подключать нужные platforms;
- подключать packages;
- подключать templates;
- подключать tools/MCP capabilities;
- задавать project-specific overrides;
- хранить assignments;
- хранить artifacts;
- хранить execution contexts;
- хранить logs;
- хранить handoffs;
- хранить reviews;
- хранить ADR;
- работать без backend.

### 7.2.1. process-forge.yaml

`process-forge.yaml` — root manifest проекта.

Он должен описывать:

- schema version;
- project id;
- project name;
- ProcessForge version;
- paths;
- workplace references;
- package references;
- process definitions;
- templates;
- tools;
- MCP requirements;
- validation tools;
- status model;
- merge policy;
- file ownership policy;
- runner mode;
- public/private metadata.

Пример:

```yaml
schema_version: 1

process_forge:
  version: 0.1.0
  mode: file_only

project:
  id: example-project
  name: Example Project

workplace:
  reference: auto
  required_capabilities:
    - repository.symbol_analysis
    - markdown.editing

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

merge:
  order:
    - core
    - workplace
    - organization
    - direction
    - specialization
    - platform
    - toolchain
    - project
    - process
    - stage
    - task
    - agent_profile

policies:
  one_writer_per_file_scope: true
  approved_artifacts_are_protected: true
  execution_context_is_immutable: true
```

---

# 8. Workplace layer и company layer не смешивать

Важно строго разделять:

```text
Workplace layer
= что доступно на конкретной машине

Company / organization package
= как принято работать в компании
```

Пример:

```text
Company:
- вести logs
- не менять чужие файлы
- делать review
- использовать approved templates
- не удалять protected artifacts

Workplace:
- symbolic analysis tool доступен здесь
- static analyzer запускается так
- local docs лежат здесь
- media generator доступен так
```

Company-политики могут быть knowledge packages.

Workplace-политики описывают локальную среду и ограничения конкретного устройства.

---

# 9. Cascade Merge Model

ProcessForge должен поддерживать каскадную сборку итогового контекста.

Базовый порядок:

```text
core defaults
  < workplace
  < organization
  < direction
  < specialization
  < platform
  < toolchain
  < project
  < process
  < stage
  < task
  < agent profile
```

## 9.1. Правила merge

1. Пакеты подключаются в порядке dependency graph.
2. Затем применяется порядок специфичности.
3. Scalar values переопределяются более специфичным уровнем.
4. Lists мержатся по id, если элементы имеют id.
5. Maps мержатся рекурсивно.
6. Locked policies нельзя переопределять без explicit override permission.
7. Conflicts должны фиксироваться.
8. Blocking conflict должен останавливать сборку execution context.
9. Итоговый context должен хранить список всех источников.
10. Итоговый context должен хранить точные версии всех пакетов.
11. Итоговый context должен хранить точные версии templates.
12. Нельзя молча терять правила.
13. Project-local rules могут переопределять workplace defaults только если политика разрешает override.
14. Task-level overrides должны быть максимально явными и журналироваться.

---

# 10. Основные сущности ProcessForge

## 10.1. Process Definition

Process Definition — файловое описание повторяемого процесса.

Примеры:

- software-feature-development;
- bug-fix;
- testing;
- content-management;
- article-production;
- media-generation;
- seo-audit;
- devops-operation;
- knowledge-package-improvement;
- process-version-upgrade.

Process Definition должен содержать:

- id;
- name;
- version;
- schema version;
- status;
- description;
- stages;
- roles;
- required capabilities;
- artifact definitions;
- gates;
- required packages;
- required templates;
- allowed tools;
- forbidden actions;
- process evolution policy;
- upgrade compatibility rules.

---

## 10.2. Stage Definition

Stage Definition описывает один этап процесса.

Содержит:

- id;
- title;
- description;
- required inputs;
- produced artifacts;
- required role;
- required capabilities;
- allowed tools;
- allowed templates;
- forbidden actions;
- entry gates;
- exit gates;
- logging requirements;
- handoff requirements;
- memory requirements.

---

## 10.3. Role

Role — логическая ответственность в процессе.

Примеры:

- orchestrator;
- analyst;
- architect;
- developer;
- reviewer;
- tester;
- editor;
- content-manager;
- SEO reviewer;
- media producer;
- publisher;
- DevOps engineer.

Role не равен agent.

Role отвечает на вопрос:

```text
какая ответственность нужна процессу?
```

---

## 10.4. Capability

Capability — способность, необходимая процессу, стадии, роли или task.

Примеры:

- repository_read;
- repository_write;
- symbol_analysis;
- php;
- joomla;
- markdown_editing;
- fact_checking;
- browser_research;
- image_generation;
- test_running;
- package_building;
- api_data_parsing;
- mcp_context7;
- mcp_serena.

ProcessForge должен требовать capabilities, а не жёстко привязываться к конкретному tool, если это возможно.

---

## 10.5. Tool

Tool — конкретная реализация capability.

Примеры:

- static analyzer;
- unit test runner;
- package builder;
- symbolic analysis tool;
- documentation lookup tool;
- browser;
- shell;
- image generator;
- search API parser;
- media generator;
- linter;
- packager.

Tool выполняет действие.

---

## 10.6. MCP Server

MCP Server — особый тип tool provider.

MCP должен описываться как capability provider, а не просто строка в промпте.

Пример:

```yaml
mcp_servers:
  - id: symbol-analysis
    capability: repository.symbol_analysis
    required: false

  - id: documentation-lookup
    capability: official_documentation
    required: false
```

---

## 10.7. Reusable Template

Reusable Template — проверенная заготовка для копирования и адаптации.

Template не является tool.

Различие:

```text
Tool
  → выполняет действие

Reusable Template
  → даёт стартовый материал для результата
```

Примеры:

- installer script;
- branded form field;
- docblock;
- SQL migration;
- API controller;
- test report;
- ADR;
- article outline;
- SEO audit table;
- media prompt;
- publication checklist.

Reusable Template должен иметь:

- id;
- version;
- source package;
- type;
- compatible stages;
- compatible platforms;
- placeholders;
- allowed modifications;
- forbidden modifications;
- post-copy instructions;
- validation rules;
- usage recording policy.

---

## 10.8. Template Usage

Когда агент использует reusable template, он должен фиксировать Template Usage.

Template Usage содержит:

- template id;
- template version;
- source package;
- target files;
- target artifacts;
- substitutions;
- modifications summary;
- validation result;
- used by;
- timestamp.

Это нужно для traceability.

---

## 10.9. Knowledge Package

Knowledge Package — версионируемый пакет знаний, правил, процедур, шаблонов и ссылок.

Может содержать:

- standards;
- procedures;
- policies;
- references;
- examples;
- reusable templates;
- tool requirements;
- MCP requirements;
- prompt fragments;
- quality rubrics;
- validation rules.

Package может относиться к:

- organization;
- direction;
- specialization;
- platform;
- toolchain;
- project;
- process;
- task;
- agent profile.

---

## 10.10. Assignment

Assignment — файловое задание для агента или человека.

Assignment должен содержать:

- id;
- title;
- role;
- process id/version;
- stage;
- goal;
- input artifacts;
- allowed files;
- forbidden files;
- required outputs;
- required artifacts;
- required reviews;
- allowed templates;
- allowed tools;
- quality checklist;
- completion criteria;
- log file;
- handoff requirements;
- status.

Assignment — основной способ управлять работой в file-only mode.

Пример:

```markdown
# Assignment: PF-A01 — Define ProcessForge Core Model

## Status

ready

## Role

Process Architect

## Goal

Define the initial ProcessForge core file model.

## Allowed files

- artifacts/core-file-flow-spec.md
- artifacts/status-model.md
- adr/0001-core-file-model.md

## Forbidden files

- tools/**
- examples/**
- packages/**

## Required outputs

- updated core file model
- status model
- ADR
- handoff note

## Quality gates

- no product dependency on backend
- no public reference to internal prototypes
- machine-readable status ids
```

---

## 10.11. Execution Context Package

Execution Context Package — immutable snapshot для конкретного assignment.

Содержит:

- context id;
- assignment id;
- process id/version;
- stage;
- role;
- task input;
- workplace references;
- project manifest hash;
- package versions;
- template versions;
- selected tools;
- selected MCP;
- allowed actions;
- forbidden actions;
- required outputs;
- required artifacts;
- quality gates;
- memory policy;
- checksums.

После создания ECP не редактируется.

Если входные данные изменились, создаётся новый ECP.

---

## 10.12. Artifact

Artifact — результат процесса, стадии или assignment.

Artifact должен иметь:

- id;
- type;
- title;
- stable id, если нужен;
- process id/version;
- status;
- owner role;
- source assignment;
- content reference;
- checksum;
- created/updated timestamps;
- review status;
- protection policy.

Artifact lifecycle:

```text
missing
draft
ready_for_review
approved
rejected
stale
superseded
archived
```

Использовать только machine-readable status ids.

---

## 10.13. Review

Review — проверка artifact, assignment result, process definition или package.

Review содержит:

- reviewed object;
- reviewer;
- criteria;
- result;
- findings;
- blocking issues;
- evidence;
- recommendation;
- timestamp.

Review result statuses:

```text
pass
pass_with_conditions
warn
fail
skipped
```

---

## 10.14. Handoff

Handoff — передача работы между исполнителями.

Содержит:

- from;
- to;
- objective;
- current status;
- input artifacts;
- changed files;
- used templates;
- known issues;
- risks;
- next steps;
- forbidden assumptions.

---

## 10.15. Log

Log — append-only журнал работы агента или человека.

Log должен фиксировать:

- timestamp;
- actor;
- role;
- task/assignment;
- files changed;
- artifacts changed;
- templates used;
- tools used;
- decisions;
- risks;
- next steps.

---

## 10.16. ADR

ADR фиксирует значимые решения.

Использовать для:

- core file model;
- workplace model;
- merge model;
- package model;
- template model;
- execution context model;
- process evolution model;
- runner protocol draft;
- validation strategy.

---

# 11. Process Evolution и safe process upgrade

ProcessForge должен с самого начала поддерживать безопасную эволюцию процессов.

Process Version immutable.

Запущенный или выполненный процесс нельзя молча перевести на новую версию, если это может разрушить уже достигнутый результат.

Правила безопасного обновления должны жить в конкретном Process Definition, а не быть одной глобальной логикой.

## 11.1. Process Evolution Policy

Process Definition должен описывать:

- можно ли обновлять active runs;
- какие stages protected;
- какие artifacts protected;
- какие изменения safe;
- какие risky;
- какие blocked;
- какие требуют approval;
- какие требуют migration;
- какие gates нужно переоценить;
- какие artifacts становятся stale.

Пример:

```yaml
evolution_policy:
  active_run_upgrade:
    default: manual_only

  protected_artifacts:
    - scope-document
    - approved-draft
    - assurance-report

  safe_changes:
    - add_optional_artifact
    - add_optional_stage_after_current
    - add_non_blocking_gate
    - add_template

  blocked_changes:
    - remove_existing_artifact_definition
    - rename_artifact_without_stable_id_mapping
    - add_required_stage_before_completed_stage
    - change_approved_artifact_meaning

  requires_approval:
    - add_required_gate
    - add_required_artifact
    - change_exit_criteria
```

## 11.2. Artifact-centered compatibility

Обновление процесса оценивается через artifacts.

Вопросы:

1. Какие artifact definitions изменились?
2. Какие artifact instances уже существуют?
3. Какие artifacts approved?
4. Какие artifacts protected?
5. Какие можно перенести?
6. Какие требуют migration?
7. Какие требуют revalidation?
8. Какие станут stale?
9. Какие потеряют definition?
10. Какие achieved results будут разрушены?

Если новая версия процесса не может объяснить, что делать с existing approved/protected artifacts, обновление блокируется.

## 11.3. Process Upgrade Assessment

Process Upgrade Assessment — отдельный artifact.

Содержит:

- current process version;
- target process version;
- affected stages;
- affected artifacts;
- preserved artifacts;
- artifacts requiring migration;
- artifacts requiring revalidation;
- gates requiring re-run;
- blocking conditions;
- recommendation;
- human-readable explanation.

Результаты:

```text
safe
requires_approval
requires_migration
blocked
```

---

# 12. File-based multi-agent rules

ProcessForge должен поддерживать мультиагентную работу уже в file-only mode.

## 12.1. Один writer на область

Главное правило:

```text
One file scope = one responsible writer.
```

Если два агента должны работать параллельно, оркестратор обязан:

- разделить allowed files;
- или назначить последовательную работу;
- или использовать отдельные branches/worktrees;
- или назначить одного writer и второго reviewer.

## 12.2. Assignment boundaries

Каждый агент получает assignment с:

- allowed files;
- forbidden files;
- required outputs;
- log file;
- handoff rules;
- completion criteria.

Агент не должен выходить за границы assignment.

## 12.3. Субагенты

Субагенты по умолчанию должны использоваться для:

- read-only research;
- review;
- consistency checks;
- schema checks;
- documentation checks;
- impact analysis.

Субагентам нельзя давать write scope в те же файлы, где работает основной агент, если это не указано явно.

## 12.4. Worktree recommendation

Для параллельной работы над кодом или большим количеством файлов рекомендуется использовать git worktree:

```text
main repository
agent-a-worktree
agent-b-worktree
agent-c-worktree
```

Но ProcessForge как файловый продукт не должен требовать git worktree обязательно.

---

# 13. Optional runtime/supervisor model

В MVP runner не обязателен, но файловая структура должна предусматривать будущий runtime layer.

Рекомендуемая будущая структура:

```text
runtime/
├── queue/
│   ├── ready/
│   ├── running/
│   ├── submitted/
│   ├── completed/
│   └── failed/
├── events/
├── locks/
├── agents/
└── supervisor.log
```

ProcessForge должен описывать три режима:

```text
manual
local_supervisor
managed
```

В первом релизе достаточно `manual`.

Если будет реализован локальный runner, он должен:

- читать assignments;
- создавать execution contexts;
- запускать agents;
- следить за timeout;
- собирать logs/artifacts;
- создавать events;
- не требовать external backend.

---

# 14. Agent boot sequence

ProcessForge должен иметь короткую инструкцию для агента.

Создать файл:

```text
AGENTS.md
```

или:

```text
PROCESSFORGE.md
```

Базовая последовательность агента:

```text
1. Прочитать project AGENTS.md.
2. Прочитать process-forge.yaml.
3. Определить workplace layer.
4. Прочитать assignment.
5. Прочитать или создать execution context package.
6. Проверить allowed files и forbidden files.
7. Подключить нужные packages/templates/tools.
8. Выполнить задачу.
9. Зафиксировать artifacts.
10. Записать log.
11. Создать review request или handoff.
12. Не выходить за scope assignment.
```

---

# 15. Validation tools

ProcessForge должен иметь валидаторы.

Минимум:

```text
processforge validate
```

или отдельные scripts:

```text
validate-process-definitions
validate-package-manifests
validate-template-manifests
validate-assignments
validate-execution-contexts
validate-checksums
```

## 15.1. Structural validation

Проверять:

- required fields;
- schema version;
- valid ids;
- valid statuses;
- paths;
- YAML/JSON syntax.

## 15.2. Semantic validation

Проверять:

- gates referenced by stages exist;
- artifacts referenced by stages exist;
- protected artifacts exist;
- stable ids unique;
- templates referenced by processes exist;
- packages referenced by project exist;
- assignment allowed files do not conflict with another running assignment;
- ECP has immutable checksum;
- statuses use machine ids.

## 15.3. Integrity validation

Проверять:

- checksums;
- changed files;
- artifacts modified after approval;
- stale ECP;
- changed templates after use;
- отсутствие запрещённых публичных references.

---

# 16. Публичная чистота продукта

Перед любым release candidate выполнить public-cleanliness review.

Проверить, что публичные файлы не содержат:

- `.webtolk`;
- имён старых внутренних прототипов;
- локальных абсолютных путей;
- личных путей пользователя;
- приватных names/hosts;
- секретов;
- временных research notes;
- внутренних scratch comments.

Публичные файлы:

```text
README.md
AGENTS.md
process-forge.yaml
docs/**
schemas/**
processes/**
packages/**
templates/**
examples/**
tools/**
LICENSE
CHANGELOG.md
```

Если в процессе разработки нужны comparison notes с `.webtolk`, хранить их в приватной рабочей области, не входящей в релиз.

---

# 17. Рекомендуемая структура репозитория ProcessForge

Для нового clean-start продукта использовать примерно такую структуру:

```text
process-forge/
├── README.md
├── AGENTS.md
├── process-forge.yaml
├── LICENSE
├── CHANGELOG.md
│
├── docs/
│   ├── concepts/
│   │   ├── file-first-processes.md
│   │   ├── workplace-layer.md
│   │   ├── project-flow-layer.md
│   │   ├── cascade-merge.md
│   │   ├── execution-context-package.md
│   │   ├── reusable-templates.md
│   │   ├── process-evolution.md
│   │   └── multi-agent-file-flow.md
│   ├── authoring/
│   │   ├── process-authoring.md
│   │   ├── package-authoring.md
│   │   ├── template-authoring.md
│   │   └── assignment-authoring.md
│   └── runner-protocol-draft.md
│
├── schemas/
│   ├── process-forge-manifest.schema.json
│   ├── workplace.schema.json
│   ├── process-definition.schema.json
│   ├── package-manifest.schema.json
│   ├── reusable-template.schema.json
│   ├── assignment.schema.json
│   ├── execution-context-package.schema.json
│   ├── artifact.schema.json
│   ├── review.schema.json
│   └── handoff.schema.json
│
├── processes/
│   ├── software-feature-development.yaml
│   ├── bug-fix.yaml
│   ├── content-production.yaml
│   ├── testing.yaml
│   ├── knowledge-package-improvement.yaml
│   └── process-version-upgrade.yaml
│
├── packages/
│   ├── process-forge-core.yaml
│   ├── process-forge-software-development.yaml
│   ├── process-forge-content.yaml
│   ├── process-forge-testing.yaml
│   └── process-forge-knowledge-governance.yaml
│
├── templates/
│   ├── assignment-template.md
│   ├── artifact-template.md
│   ├── handoff-template.md
│   ├── review-template.md
│   ├── adr-template.md
│   ├── process-definition-template.yaml
│   ├── package-manifest-template.yaml
│   ├── reusable-template-template.yaml
│   └── execution-context-package-template.yaml
│
├── examples/
│   ├── software-project/
│   ├── content-project/
│   ├── testing-project/
│   └── media-generation-project/
│
├── tools/
│   ├── validate-process-forge-schemas.py
│   ├── validate-process-forge-checksums.py
│   └── README.md
│
├── assignments/
│   └── README.md
│
├── artifacts/
│   └── README.md
│
├── contexts/
│   └── README.md
│
├── logs/
│   └── README.md
│
├── reviews/
│   └── README.md
│
├── handoffs/
│   └── README.md
│
└── adr/
    └── README.md
```

В чистом ProcessForge-репозитории не должно быть production-кода будущих backend-продуктов.

---

# 18. Этапы разработки ProcessForge

## Phase 0. Bootstrap

Цель:

```text
Создать минимальный файловый skeleton ProcessForge.
```

Сделать:

- README.md;
- AGENTS.md;
- process-forge.yaml;
- docs/concepts;
- базовые директории;
- базовые templates;
- initial ADR;
- initial assignments для агентов.

## Phase 1. Pattern research from `.webtolk`

Цель:

```text
Извлечь проверенные паттерны из .webtolk, не копируя старую структуру.
```

Сделать внутренние рабочие notes:

- какие паттерны worth preserving;
- какие паттерны устарели;
- какие паттерны нужно обобщить;
- какие элементы применимы только к development-flow;
- какие элементы применимы универсально.

Результат этой фазы не должен попадать в публичный релиз, если содержит упоминания `.webtolk`.

Публичный результат этой фазы — только обобщённые решения ProcessForge без ссылок на источник.

## Phase 2. Core file model

Цель:

```text
Описать базовые файловые сущности.
```

Сделать:

- core file model;
- status model;
- assignment model;
- artifact model;
- log model;
- handoff model;
- review model;
- ADR.

## Phase 3. Workplace and project layer

Цель:

```text
Формализовать global workplace layer и project flow layer.
```

Сделать:

- workplace.yaml schema;
- workplace docs;
- project process-forge.yaml schema;
- cascade references;
- example workplace;
- example project.

## Phase 4. Packages, tools, MCP, templates

Цель:

```text
Описать подключаемые знания, инструменты и шаблоны.
```

Сделать:

- package manifest schema;
- reusable template schema;
- tool capability model;
- MCP model;
- package examples;
- template examples.

## Phase 5. Process definitions

Цель:

```text
Создать первые универсальные seed-процессы.
```

Сделать:

- software-feature-development;
- bug-fix;
- testing;
- content-production;
- knowledge-package-improvement;
- process-version-upgrade.

## Phase 6. Execution Context Package

Цель:

```text
Формализовать immutable context snapshot.
```

Сделать:

- ECP schema;
- ECP template;
- prompt template;
- example ECP;
- checksum rules;
- stale context rules.

## Phase 7. Process evolution

Цель:

```text
Безопасная эволюция процессов.
```

Сделать:

- process evolution docs;
- upgrade assessment template;
- artifact-centered compatibility rules;
- example safe/risky/blocked upgrades.

## Phase 8. Validation

Цель:

```text
Минимальные валидаторы.
```

Сделать:

- schema validator;
- checksum validator;
- semantic validation MVP;
- validation report template;
- public cleanliness check.

## Phase 9. Examples

Цель:

```text
Показать, что ProcessForge не только про разработку.
```

Сделать examples:

- software project;
- content management project;
- testing project;
- media generation project.

## Phase 10. Optional runner protocol draft

Цель:

```text
Спроектировать будущий local supervisor mode без обязательной реализации.
```

Сделать:

- runtime directory spec;
- queue status model;
- event model;
- lock/lease draft;
- runner protocol draft.

Реализацию runner не делать в MVP, если она мешает выпуску файлового продукта.

---

# 19. Разделение работы между агентами

Оркестратор должен разделить разработку ProcessForge на независимые направления.

## Agent A — Product and Core Concept Architect

Ответственность:

- публичное позиционирование;
- границы продукта;
- README;
- core concepts;
- терминология;
- принцип автономной работы без backend;
- отсутствие публичных references на старые внутренние прототипы.

Allowed files:

```text
README.md
docs/concepts/**
adr/0001-*.md
```

## Agent B — Pattern Research Agent

Ответственность:

- изучить `.webtolk` как источник паттернов;
- выписать reusable patterns;
- выписать паттерны, которые нельзя переносить напрямую;
- подготовить внутренний research summary для оркестратора;
- не писать публичную документацию ProcessForge напрямую.

Allowed files:

```text
private-notes/**
logs/agent-b-pattern-research.md
handoffs/agent-b-to-orchestrator.md
```

Если в проекте нет `private-notes/`, оркестратор должен создать приватную рабочую область или указать иной путь вне публичного релизного дерева.

## Agent C — File Model Architect

Ответственность:

- assignment model;
- artifact model;
- log model;
- handoff model;
- review model;
- status model.

Allowed files:

```text
docs/concepts/file-first-processes.md
docs/authoring/**
schemas/assignment.schema.json
schemas/artifact.schema.json
schemas/review.schema.json
schemas/handoff.schema.json
templates/*template*
```

## Agent D — Workplace and Cascade Architect

Ответственность:

- workplace layer;
- project layer;
- cascade merge;
- override rules;
- locked policies.

Allowed files:

```text
docs/concepts/workplace-layer.md
docs/concepts/project-flow-layer.md
docs/concepts/cascade-merge.md
schemas/workplace.schema.json
schemas/process-forge-manifest.schema.json
```

## Agent E — Package and Template Architect

Ответственность:

- knowledge package model;
- reusable template model;
- template usage;
- package examples;
- template examples.

Allowed files:

```text
docs/concepts/reusable-templates.md
docs/authoring/package-authoring.md
docs/authoring/template-authoring.md
schemas/package-manifest.schema.json
schemas/reusable-template.schema.json
packages/**
templates/**
```

## Agent F — Process Definition Architect

Ответственность:

- process definition schema;
- seed processes;
- roles/capabilities;
- gates;
- artifact definitions.

Allowed files:

```text
docs/authoring/process-authoring.md
schemas/process-definition.schema.json
processes/**
```

## Agent G — Execution Context Architect

Ответственность:

- ECP model;
- ECP schema;
- prompt template;
- checksum/stale context rules.

Allowed files:

```text
docs/concepts/execution-context-package.md
schemas/execution-context-package.schema.json
templates/execution-context-package-template.yaml
templates/execution-context-prompt-template.md
contexts/**
```

## Agent H — Process Evolution Architect

Ответственность:

- safe process evolution;
- process upgrade assessment;
- artifact-centered compatibility;
- migration rules.

Allowed files:

```text
docs/concepts/process-evolution.md
processes/process-version-upgrade.yaml
templates/process-upgrade-assessment-template.md
schemas/process-upgrade-assessment.schema.json
```

## Agent I — Validation Tooling Developer

Ответственность:

- schema validators;
- checksum validators;
- semantic validation;
- public cleanliness validation;
- validation docs.

Allowed files:

```text
tools/**
schemas/**
docs/validation/**
```

Не менять schemas без handoff с ответственным архитектором соответствующей схемы.

## Agent J — Examples and Documentation Agent

Ответственность:

- examples;
- guides;
- quickstart;
- non-development examples.

Allowed files:

```text
examples/**
docs/getting-started.md
docs/examples/**
```

## Agent K — QA / Public Cleanliness Review Agent

Ответственность:

- review artifacts;
- consistency checks;
- status model consistency;
- public/private terminology review;
- проверка отсутствия `.webtolk` в публичных файлах;
- проверка отсутствия локальных путей и приватных данных.

Allowed files:

```text
reviews/**
logs/qa-reviewer.md
```

QA agent не пишет production specs без handoff.

---

# 20. Правила работы агентов при разработке ProcessForge

Каждый агент обязан:

1. Прочитать этот мастер-промпт.
2. Прочитать `AGENTS.md`, если он уже создан.
3. Работать только в allowed files.
4. Не менять чужие файлы без handoff.
5. Создавать log.
6. Создавать handoff при передаче работы.
7. Фиксировать важные решения в ADR.
8. Использовать machine-readable ids.
9. Не добавлять backend-зависимости.
10. Не добавлять Joomla-специфичные требования в core.
11. Не превращать ProcessForge в development-only system.
12. Не делать runner обязательным.
13. Не усложнять MVP за счёт будущего managed mode.
14. Не переносить старую структуру `.webtolk` механически.
15. Не допускать упоминания `.webtolk` в публичных файлах ProcessForge.
16. Если агент работает с `.webtolk`, результат с упоминанием `.webtolk` должен оставаться во внутренней рабочей области.

Log format:

```markdown
## YYYY-MM-DD HH:MM — <agent role>

Task:
Files changed:
Artifacts changed:
Templates used:
Decisions:
Risks:
Next steps:
Handoff:
```

Handoff format:

```markdown
# Handoff: <from> → <to>

Objective:
Current status:
Input artifacts:
Files changed:
Files not to touch:
Known issues:
Required checks:
Next recommended action:
```

---

# 21. Первый рабочий план оркестратора

Начни работу так:

## Step 1. Получить пути от пользователя

Перед работой с существующими материалами запроси или используй переданные пользователем пути к:

- будущему репозиторию ProcessForge;
- `.webtolk`, если нужно изучать паттерны;
- глобальному AGENTS.md рабочего места;
- платформам;
- пакетам знаний;
- tools;
- MCP;
- templates;
- локальным рабочим директориям.

Не придумывай пути.

## Step 2. Создать чистую структуру ProcessForge

Создать минимальный skeleton:

```text
README.md
AGENTS.md
process-forge.yaml
docs/concepts/
docs/authoring/
schemas/
processes/
packages/
templates/
examples/
tools/
assignments/
artifacts/
contexts/
logs/
reviews/
handoffs/
adr/
```

Если нужны private notes для анализа `.webtolk`, создать приватную рабочую область, не входящую в публичный релиз.

## Step 3. Создать начальные ADR

Минимум:

```text
adr/0001-processforge-product-boundary.md
adr/0002-workplace-and-project-layer.md
adr/0003-cascade-merge-model.md
adr/0004-execution-context-package.md
adr/0005-reusable-template-model.md
adr/0006-process-evolution-model.md
adr/0007-validation-strategy.md
adr/0008-public-cleanliness-policy.md
```

## Step 4. Создать assignments для агентов

Создать:

```text
assignments/agent-a-product-core.md
assignments/agent-b-pattern-research.md
assignments/agent-c-file-model.md
assignments/agent-d-workplace-cascade.md
assignments/agent-e-packages-templates.md
assignments/agent-f-process-definitions.md
assignments/agent-g-execution-context.md
assignments/agent-h-process-evolution.md
assignments/agent-i-validation.md
assignments/agent-j-examples-docs.md
assignments/agent-k-qa-public-cleanliness.md
```

## Step 5. Запустить file-only dogfooding

Разработка ProcessForge должна сразу идти через сам ProcessForge:

```text
assignments
→ logs
→ artifacts
→ handoffs
→ reviews
→ ADR
```

Даже если schemas и validators ещё не готовы, процесс должен использовать собственную файловую дисциплину.

## Step 6. Свести результаты

Оркестратор должен:

- собрать результаты агентов;
- проверить конфликты терминологии;
- проверить структуру;
- проверить отсутствие backend-зависимостей;
- проверить отсутствие публичных legacy references;
- проверить отсутствие `.webtolk` в публичных файлах;
- создать review;
- создать consolidated roadmap.

---

# 22. Критерии успеха первого релиза ProcessForge

Первый релиз ProcessForge успешен, если:

1. Новый пользователь может скопировать ProcessForge в проект.
2. Есть понятный `README.md`.
3. Есть понятный `AGENTS.md`.
4. Есть `process-forge.yaml`.
5. Есть workplace layer spec.
6. Есть project flow layer spec.
7. Есть cascade merge model.
8. Есть минимум 3 разных процесса, включая хотя бы один не-development process.
9. Есть package manifest model.
10. Есть reusable template model.
11. Есть assignment model.
12. Есть artifact/review/handoff/log model.
13. Есть execution context package model.
14. Есть process evolution model.
15. Есть validation scripts.
16. Есть examples.
17. Есть multi-agent file-only working rules.
18. Нет обязательной зависимости от backend.
19. Нет обязательной зависимости от runner.
20. Нет публичного упоминания `.webtolk`.
21. Core не привязан к Joomla.
22. Core не привязан только к software development.
23. Нет локальных абсолютных путей в публичных файлах.
24. Нет приватных machine names, secrets или scratch notes в публичных файлах.

---

# 23. Что оставить на будущие продукты

В этом мастер-промпте не разрабатывать:

```text
WT AI Control Center
Joomla backend
web UI
database schema
runner API
agent workplace heartbeat
package update server
managed synchronization
```

Можно только предусмотреть future-friendly design:

- stable ids;
- machine-readable manifests;
- checksums;
- source paths;
- package versions;
- execution context snapshots;
- import/export-friendly formats;
- optional local runner protocol draft.

Runner можно описать как draft, но не делать его обязательным.

---

# 24. Финальная инструкция оркестратору

Действуй так:

1. Проектируй ProcessForge как самостоятельный файловый продукт.
2. Не начинай WTAICC-разработку в этом проекте.
3. Не делай ProcessForge зависимым от будущего backend.
4. Не делай ProcessForge зависимым от runner.
5. Используй `.webtolk` только как внутренний источник проверенных паттернов.
6. Не копируй `.webtolk` механически.
7. Не делай `.webtolk` частью публичного продукта.
8. Не допускай упоминания `.webtolk` в публичных файлах ProcessForge.
9. Сначала создай чистую структуру.
10. Затем опиши core file model.
11. Затем workplace/project cascade.
12. Затем packages/templates/tools/MCP.
13. Затем process definitions.
14. Затем execution context package.
15. Затем process evolution.
16. Затем validation.
17. Затем examples.
18. Разработку самого ProcessForge веди через ProcessForge assignments, logs, reviews, handoffs и ADR.
19. Соблюдай one-writer-per-file-scope.
20. Для субагентов по умолчанию используй read-only/review/research задачи.
21. Все machine-readable ids должны быть стабильными.
22. Все публичные документы должны говорить только о ProcessForge.
23. Пути к `.webtolk`, глобальным инструкциям, платформам, пакетам, tools и MCP бери только из входных данных пользователя.
