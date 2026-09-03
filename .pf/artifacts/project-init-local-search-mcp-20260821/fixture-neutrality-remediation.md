# Нейтрализация fixture для публичного релиза

Дата: 2026-08-21

В acceptance fixture `tools/smoke_project_init_acceptance.py` нормализованный
тестовый идентификатор платформы заменён с `platform.fixture-platform` на
`platform.test-fixture`. Смысл проверки platform binding не изменён; literal
больше не совпадает с запрещённым для public surface доменным маркером.

Проверено:

- `python tools/smoke_project_init_acceptance.py` — PASS;
- `python bin/pf.py release-test --root <isolated-copy> --public --fail-fast`
  проходит public-cleanliness этап (финальный прогон зафиксирован отдельным
  release evidence).
