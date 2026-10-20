# Предметная модель исправления контекста

## domain-model
Source fingerprint: источник с id, безопасным display path, kind и raw checksum. Raw hash остаётся свидетельством фактических байтов.
Context freshness: соответствует ли зафиксированный снимок текущим входам проекта; отдельна от execution/resource readiness.
Официальный process pack: выбранные активным реестром manifest и project-classifier YAML, доступные через существующий OfficialProcessPackReader.
LF/CRLF являются двумя поддержанными представлениями одного текста official pack; представления других источников здесь не переопределяются.

## business-rules
- Сначала штатное точное сравнение raw hashes.
- При расхождении только official-process-pack допускается доказать равенство recorded hash одному из равномерных LF/CRLF представлений текущего текста.
- Перед таким доказательством новый raw hash прочитанных байтов обязан совпасть с raw hash исходного наблюдения этой операции. Изменение между чтениями не принимается за свежесть.
- Действительное изменение любой иной части байтов и всякое add/remove сохраняет stale.
- Existing snapshot/raw hashes не переписываются; политика распространяется на прежние снимки без повторного refresh.
- Семантическая YAML-дедупликация, whitespace/comment normalization и общая нормализация security/evidence digests запрещены.
- Никакого persistent cache: следующее обращение снова наблюдает фактические документы и реестр.
- Transport layer не выбирает иную политику. Missing/expired/broken/pinned-resource/execution semantics остаются прежними.

## Инварианты архитектуры
D01/D02/D06: оба интерфейса получают решение существующего общего Core; права и binding не меняются.
D05/R06: холодные конструкторы, live чтение, без metadata-only shortcut.
D07/R03/R07: immutable snapshots/evidence/process/capsule pins и их байтовые digest-контракты сохранены.
D09: обычные Python modules/dataclasses и конкретные существующие readers, без Kernel/DI/bridge.
D11/R10/R12: отдельная Work, scoped writers, portable публичные отчёты; private roots только в scratch.
D03/D04/D08/D10 и остальные R01-R12 остаются защитными ограничениями; новые подсистемы не реализуются.

## domain-reviewed
Модель отличает текстовую эквивалентность official pack от целостности артефактов, источникового drift и инфраструктурной доставки.

