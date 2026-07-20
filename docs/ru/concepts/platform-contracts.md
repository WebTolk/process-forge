# Platform Contracts

Platform contract - это composition package, а не просто метка проекта.

Контракт может включать:

- platform knowledge packages
- required capabilities
- language и toolchain packages
- official documentation references
- source code references
- snippets и examples
- templates
- tools
- MCP providers
- local test environment notes

Project initialization может выбрать platform contract из явного выбора
оператора, `project_type_hints` или generic detection rules, объявленных в
platform manifests. Ядро ProcessForge ничего не знает о конкретных
implementation, documentation, content, operations или business domains.
Platforms являются data-driven contracts, загружаемыми из manifests.

## Capability, Knowledge Package, Platform

- Capability описывает, что агенту или процессу может понадобиться делать.
- Knowledge package описывает, где агент читает правила, документацию, примеры
  и стандарты.
- Platform contract собирает application или domain stack поверх packages,
  templates, tools, MCP providers, capabilities и processes.

Base languages и web technologies относятся к capabilities и knowledge
packages. Они не являются platform contracts. Project platform может включать
такие знания напрямую или наследовать их от parent platform.

Resource authoring использует `platform-create`, чтобы записывать contracts в
workplace platform contract root. `project_type_hints` связывает contract с
`project-onboard`: matching hints добавляют platform в project snapshot вместе
с linked knowledge packages и templates.

Missing required platform capabilities блокируют strict automation. Missing
optional capabilities дают warnings.

## Resource Management Contract Use

Platform contracts могут ссылаться на knowledge packages, knowledge resources,
tools, MCP providers и templates через отдельные required и recommended groups.

- `requires` означает, что missing entries являются blocking и doctor checks
  должны FAIL.
- `includes` означает, что missing entries advisory и doctor checks должны WARN.

Contracts не копируют heavy resources в projects; snapshots включают selected
resource index records с `load_policy`.

Используйте `extends` для inheritance и `requires.platforms` для dependency
checks:

```yaml
extends:
  - id: platform.example-parent
    version: "^1.0"
    required: true

requires:
  platforms:
    - id: platform.example-parent
      version: "^1.0"
      required: true
```

Parent platforms разрешаются первыми. Их resources объединяются до применения
child platform. `project-onboard` записывает deterministic `platform_stack` и
inherited knowledge packages.

Не начинайте с platform contract, если его обязательные packages, templates,
tools, MCP servers, processes, coding standards или capabilities ещё не
существуют. Сначала создайте или зарегистрируйте зависимости.

Example only: документация может описывать реальный stack вроде
Joomla -> JoomShopping, где child platform inherits parent context. Такой
product-specific stack должен жить в workplace data или docs/examples, а не в
core code paths ProcessForge.
