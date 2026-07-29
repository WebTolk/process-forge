# Специализации

Specialization в ProcessForge - это resource profile рабочего места или
проекта. Она описывает knowledge packages, tools, MCP providers, templates и
capabilities, которые активируются для специалиста в выбранном platform stack.
Это не agent profile, не process, не platform и не mini-process.

PF core не поставляет обязательный встроенный каталог специализаций и не
хардкодит product, platform, tool, package, role или capability IDs. Пользователь
создает specializations после workplace initialization, когда уже существуют
platform contracts, knowledge packages, tools, MCP providers и templates, на
которые specialization ссылается.

Specializations живут вне distribution root:

- `<workplace>/specializations/`
- `<workplace>/registries/specializations.yaml`
- `<project>/.pf/specializations/`
- `<project>/.pf/specializations/overrides/`

`platform_bindings` делают specialization platform-specific, но не превращают ее
в platform. Один platform stack может поэтому давать разные активные resources и
provided capabilities для разных specializations.

Specialization не владеет workflow stages, gates, acceptance criteria, required
artifacts или required evidence. Process владеет этими полями и объявляет
abstract capability requirements. Resolver проверяет, предоставляет ли selected
specialization и ее platform binding эти requirements.

Capabilities - непрозрачные ID из данных. Ядро ProcessForge не поставляет
каталог software, web, content, media, legal или других доменных capabilities и
не удовлетворяет требования specialization/process через встроенный provider.
Если active specialization, activated resources, platform data или project
overrides не предоставляют требуемую capability, resolver записывает ее как
`unsatisfied`.

Примеры в документации и smokes используют `fixture.*` IDs и являются только
examples.
