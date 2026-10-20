# Модель установки

## domain-model / domain-review
Сущности: принятый archive SHA, source build 526c5d13, текущий manifest d6eb1412,
один новый update journal с backup, installed manifest/source, неизменный project
snapshot ctx-20261020-072238-da5df2, реальный connected host следующей сессии.
Ownership задаёт native manifest: 5 заменяемых PF-owned paths, неизвестные файлы
не включаются в операции. Workplace migration operations пусты.

## domain-approved
Оператор явно разрешил установку. Scope разрешает только native delivery данного
пакета и собственный учёт; исходники, чужие OOP54-55 и сервисы не меняются.
Installed CLI и actual connected-host acceptance остаются разными доказательствами.
Снимок не refresh; version 1.2.0 dev не переименовывается в 1.3.0-alpha1.
