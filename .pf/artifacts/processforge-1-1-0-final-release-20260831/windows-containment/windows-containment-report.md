# Windows raw-ingress containment race

## Наблюдение

В чистом exact-tag release-test один из 12 параллельных SessionStart получил
`path escapes runtime root` для существовавшего в этот момент lock path с
Win32 extended spelling `\\?\C:\...\.ingress.lock`. Остальные 11 запросов
вернули HTTP 200. Тот же smoke до этого прошёл в source assurance и трижды
подряд прошёл после отказа, что подтверждает race-зависимый характер.

## Причина и исправление

`Path.resolve()` на Windows мог вернуть обычное написание для root и extended
написание для одновременно созданного lock file. Семантически одинаковые пути
не проходили `relative_to`. Перед containment comparison теперь
нормализуются `\\?\C:\...` и `\\?\UNC\...`; symlink-aware `resolve()` и
запрет реального выхода за root сохранены.

## Проверка

- Добавлены детерминированные drive/UNC normalization assertions.
- Обязательны повторные `smoke_long_lived_runtime.py`, полный clean source
  release-test и extracted archive test.
