# Platform Contract Authoring

Platform contracts композируют required и recommended capabilities, packages,
tools, MCP и templates.

ProcessForge core domain-agnostic. Он не знает о конкретных implementation,
documentation, content, operations или business domains. Platform behavior
приходит из manifests и policy data.

Используйте platform contracts для domain или application stacks, а не для base
language или web-technology knowledge. Base technologies сначала оформляются
как knowledge packages и capabilities, затем включаются в platform contract,
которому они нужны.

Не создавайте platform contracts для base technology knowledge. Создавайте
knowledge packages и capabilities first, затем включайте их из нужного platform
contract.

Создание и проверка через Python launcher:

```bash
python bin/pf.py platform-create --workplace ./workplace --id platform.example-app --title "Example Application Platform" --project-type example-app --apply
python bin/pf.py platform-contract-doctor --workplace ./workplace --platform platform.example-app
```

Используйте `requires` для items, без которых platform unsafe или incomplete.
Doctor checks должны fail, когда required contracts или required resources
отсутствуют.

Используйте `includes` для recommended knowledge, templates, tools и MCP
providers. Missing recommended entries должны warn.

Держите required и recommended lists раздельно, чтобы snapshots могли ясно их
показывать, а doctor output мог сопоставлять missing entries с FAIL или WARN.

`project_type_hints` связывает contract с `project-onboard`. Когда project
onboarded с matching type, project context snapshot записывает platform и linked
resources by id.

Создайте или зарегистрируйте dependencies до создания platform contract:
knowledge packages, reusable templates, tools, MCP servers, processes, coding
standards и capabilities.

Используйте `extends` для inheritance и `requires.platforms` для dependency
checks. Joomla -> JoomShopping - только пример; любой parent/child stack
объявляется так же через manifest.

После authoring запускайте `platform-contract-doctor`. Он разрешает
parent-first platform stack, проверяет missing parents и circular inheritance,
проверяет inherited required resources и записывает resolved stack snapshot.
