# Process Definition, Run, Task, Iteration

Process definition описывает правила работы: stages, roles, artifacts, gates,
events, tools и evolution policy.

Run применяет процесс к конкретной рабочей сессии. Task разбивает run на
управляемые части. Iteration фиксирует фактические попытки выполнения.

Эта модель делает работу агента проверяемой: можно увидеть, какой процесс был
выбран, какие задачи созданы, какие artifacts появились и какие reviews или
handoffs закрывают работу.
