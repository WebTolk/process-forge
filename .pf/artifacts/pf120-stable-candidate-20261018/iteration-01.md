# Согласование stable metadata при будущей публикации

Обнаружено при подготовке: tools/release_metadata_contract.py и связанные stable metadata smokes намеренно описывают действующий1.1.0; один smoke отдельно запрещает тестовую строку1.2.0. Это корректный текущий baseline, но его нельзя оставить неизменным вместе с будущим active feed1.2.0.

Решение в рамках artifact-only preparation: подготовить и проверить отдельный promotion patch под будущий metadata commit. Он согласует historical sidecar1.2.0, mutable feed1.2.0, связанные release metadata expectations и их checksum inventory. Применение к live source, активному каналу и публичным assets сейчас не выполняется.

Такой metadata commit по maintainer contract идёт после tag/build/asset publication и не меняет immutable release archive/source commit. Проверки нового feed выполняются на изолированной preview-копии с фактическим canonical ZIP/sidecar. Полный source/consumer на release commit остаётся отдельным доказательством. Metadata/QA изменение не переименовывается в продуктовый feature или silently included в уже упакованный архив.

Исторический1.1.0 feed/asset discrepancy оператором явно waived; текущие1.1.0 public assets скачаны только для read-only isolated previous-client discovery. Их фактический sidecar/hash проверяется без попытки исправлять исторический канал.
