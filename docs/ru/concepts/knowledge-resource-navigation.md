# Навигация knowledge resources

Knowledge packages описывают, как агентам находить reusable documentation,
snippets, local mirrors, API snapshots, examples и standards без копирования
тяжёлых source trees в public package manifests.

Private local documentation и source snapshots должны ссылаться через workplace
knowledge roots.

```yaml
path_ref:
  registry: knowledge_roots
  id: local-docs
  relative_path: "official/example"
```

## Base technology packages

Base languages и web technologies - это reusable knowledge packages и
capabilities, а не platform contracts. Project platform contract может включать
такие packages напрямую или наследовать их от parent platform.

Dependencies knowledge packages тоже управляются manifests. Package может
объявить `dependencies` или `requires.knowledge_packages`, а doctors читают эти
dependencies generic для любого package id.

## Application or domain packages

Application и domain knowledge живёт в явных packages, выбранных workplace.
Package должен ясно описывать navigation contract:

- на какой local mirror, external documentation, API snapshot или code snippet
  он указывает;
- когда агент должен его загружать;
- какие package dependencies нужно загрузить сначала;
- является ли resource required, recommended или on demand.

Если package запланирован, но resources ещё недоступны, фиксируйте documented
placeholder status, а не silent pass.

## Platform composition example

Example only: документация может описывать реальный platform stack вроде
Joomla -> JoomShopping. В таком примере child package и child platform зависят
от parent package и parent platform. Та же mechanics применяется к любому
workplace-defined parent/child platform stack; ProcessForge core не
special-case эти names.

## API packages

API knowledge packages именуются по provider:

```text
package id:   docs.api.<provider>
platform id:  platform.api-<provider>
registry id:  api-<provider>
```

Не создавайте один generic `docs.api` package для всех providers. Каждый
provider получает собственные package, platform и registry id, например
`docs.api.example-provider`, `platform.api-example-provider` и
`api-example-provider`.
