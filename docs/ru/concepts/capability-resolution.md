# Capability Resolution

Ядро ProcessForge доменно нейтрально. Оно умеет разрешать capabilities, но не
знает, какие пользовательские или workspace capabilities существуют.

Capability - это непрозрачный строковый ID. Process может требовать capability
ID, а specialization, tool, MCP provider, template, platform contract, package
или project override могут предоставлять capability ID через данные workspace
или проекта. Resolver выполняет только операции над множествами:

```text
required_capabilities
provided_capabilities
satisfied = required intersect provided
unsatisfied = required - provided
```

Ни одна capability пользовательского процесса не удовлетворяется ядром PF по
умолчанию. Внутренние операции PF, например schema validation, hash calculation,
snapshot writing и archive checking, являются runtime-механикой, а не
providers для требований пользовательских процессов.

## Источники Данных

Provided capabilities приходят только из активных данных:

- selected specialization definitions
- matched specialization `platform_bindings`
- activated tool, MCP и template definitions
- platform contracts, если они явно выбраны данными workspace/project
- project overrides и task-explicit resources
- optional workplace, project или package capability registries

Если process требует capability, которую active resource profile не
предоставляет, результатом будет `unsatisfied`, а context status -
`needs_resources`.

## Примеры

В документации используются синтетические ID:

```text
fixture.capability.a
fixture.capability.b
example.capability.domain-specific-thing
```

ID, похожие на конкретные software, media, legal или другие домены, могут
появляться только как examples в пользовательских, workspace или package
данных. Они не являются PF core defaults.
