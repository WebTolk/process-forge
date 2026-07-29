# Handoff: Domain-Neutral Core Boundary

Статус: готово к интеграции

## Доставлено

- domain-neutral core boundary;
- data-driven project classifiers и schemas/registries/templates;
- три explicit optional domain packs;
- neutralized core processes, prompts, templates и examples;
- hardcode/public-support policies;
- девять новых public smokes и адаптированные regression checks;
- EN/RU документация;
- актуальные checksum inventory, ZIP и manifest.

## Проверка следующего исполнителя

```text
python bin/pf.py release-test --root . --public
python bin/pf.py release-archive-test --archive dist/processforge.zip --manifest dist/processforge.manifest.json --root . --extracted-test full
git diff --check
```

Последний результат: все команды PASS.

## Следующие улучшения

1. Добавить `project-classifier-doctor` и явные ошибки для missing/malformed
   active registry entries.
2. Зафиксировать precedence `workplace < installed package < project <
   explicit` с last-wins и shadowing diagnostics.
3. Добавить CLI import/register classifier без implicit package activation.
4. Согласовать workplace capability registry для создания assignment capsules
   в dogfooding-проекте ProcessForge.

Commit/push выполняются отдельным поручением после завершения проверок.
