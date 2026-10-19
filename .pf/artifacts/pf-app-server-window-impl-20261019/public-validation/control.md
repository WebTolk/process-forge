# Публичная проверка server-window задачи

Дата: 2026-10-19. Исполнитель primary; дополнительного воркера нет.
Work: garage-pf-app-server-window-20261019-corrected-public-validation-scope-p.
Assignment: pf-app-server-window-20261019-corrected-public-validation-scope-primary.
Capsule: sha256:1eabe54d1d7f42e3432edcc6b84e2689902665c39038b0547734d1299485667b.
Fresh ctx-20261019-051448-f6dad2; valid/ready. Разрешены read/write_artifact,
write_product запрещён; запись только собственных artifacts/tmp/log.

## Task record / scope / brief

После фиксации docs/tests получить публичный состав по public_file_entries
существующего checksum validator. Скопировать его в собственный временный каталог
без исторических assignments, capsule и runtime журналов. Единственное явное
отличие от рабочей копии: .pf/process-forge.yaml взять из Git HEAD, сохранив
посторонние локальные Python knowledge selectors нетронутыми. Это tracked
конфигурация исходного коммита, а не автоматически подставленный seed.
Все продуктовые Python/docs текущей задачи копируются побайтно; размеры,
SHA-256 и нормализованные release SHA-256 фиксируются. checksum inventory
создаётся только внутри временной копии. Source inventory обновляет родительская
implementation Work в своей области записи после сверки изменений.

## Execution context / lifecycle mode

software-feature-development@1.2.0, supporting assurance Work primary.
Предыдущая поддерживающая Work отменена штатно до выполнения копирования:
в её scopes отсутствовали некоторые обязательные публичные root files,
а forbidden_files противоречили требуемому чтению. Капсула не редактировалась.
Этот документ уточняет прежний control: public_file_entries не подменяет
локальную конфигурацию seeds автоматически.

## Investigation / impact / domain / architecture / implementation plan

Полный source schema scan остановился на исторической assignment с неверной
execution_mode. Source cleanliness обнаружил 15 старых docs.python* ids в
локальной изменённой .pf/process-forge.yaml. Git diff подтвердил её посторонние
изменения. Исправлять ни одно из них эта задача не разрешает.
Точная публичная копия с tracked baseline config позволяет проверить поставляемый
код без приватного исторического состояния. Проверки: штатные schemas,
public-cleanliness, checksum --check, целевые smoke entrypoints. Сравнить список
новых/изменённых файлов inventory с владельцами задачи; неожиданный diff остановит
обновление source inventory. Рабочий продукт и реальные службы здесь не меняются.

Это source/public-payload evidence, не архив ZIP, установленный Core, Runtime
или проверка реального графического рабочего стола. Независимый reviewer обязан
проверить методику, точные hashes и все четыре worker reports вместе с primary.
