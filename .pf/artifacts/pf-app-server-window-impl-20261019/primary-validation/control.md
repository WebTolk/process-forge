# Проверка поставляемого состава задачи

Дата: 2026-10-19. Исполнитель: primary, дополнительного воркера нет.
Work: garage-pf-app-server-window-20261019-primary-artifact-only-validation-va.
Assignment: pf-app-server-window-20261019-primary-artifact-only-validation-validate.
Capsule checksum: sha256:01d0adcdd29d72e2402f0d7c608579c1cfffbf9a4ec2b7b2eed4846fed9d83ad.
Context: fresh ctx-20261019-051448-f6dad2, valid/ready. Продукт только читается.

## Task record / brief / scope

Проверить точный публичный состав текущего server-window изменения в отдельном
каталоге .pf/tmp/pf-app-server-window-impl-20261019/primary-validation/.
Копирование по public_file_entries существующего checksum validator сохраняет
публичные пути и штатные seeds вместо локальной приватной PF-конфигурации.
Нельзя изменять исходные продуктовые файлы, .pf/process-forge.yaml и службы.

## Execution context summary / lifecycle mode decision

Это поддерживающая Work основного исполнителя в режиме assurance; все записи
ограничены собственными артефактами/журналом/tmp. Основная Work сохраняет
интеграцию и доставку. Применяется software-feature-development@1.2.0.
Самостоятельное ревью primary эта проверка не заменяет: независимый reviewer
проверяет её отчёт и все остальные вклады.

## Investigation / impact / domain / architecture / implementation plan

Глобальные source validators ранее остановились на исторической assignment и
локальных Python knowledge ids. Это другая область, не продукт задачи.
Отдельный публичный состав позволяет проверить schemas, cleanliness и checksum
inventory без изменения локальных настроек и без скрытия исходных ошибок.
Копируем только штатный public_file_entries, сохраняем размер и SHA-256 каждого
файла и проверяем равенство источнику. Временную копию не называем установленным
Core или проверкой работающего Runtime. Реальный GUI отдельно не подтверждён.

Код, модель Core и OS adapter contracts зафиксированы в ../primary/design.md,
вклады — в ../windows/report.md и ../linux/report.md. Нового продуктового кода
в этой Work нет. После завершения worker-assurance и docs создаём копию,
выполняем выбранные проверки, сохраняем результаты, затем закрываем Work с
передачей evidence основной Work и независимому reviewer.
