# Process definition, run, task, iteration

Process definition описывает правила работы: стадии, роли, артефакты, gates,
events, инструменты и evolution policy.

Run применяет процесс к конкретной рабочей сессии. Task разбивает run на
управляемые части. Iteration фиксирует фактические попытки выполнения.

Эта модель делает работу агента проверяемой: можно увидеть, какой процесс был
выбран, какие задачи созданы, какие artifacts появились и какие reviews или
handoffs закрывают работу.

# Граница software lifecycle

Process definition описывает lifecycle, а не платформенную команду сборки или
доставки. Например, `software-feature-development` содержит условные stages
`release-delivery` и `evolve`, а package/build/install должен задаваться как
`execution_profile.delivery_profile`.
