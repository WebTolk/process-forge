# Отчет: process-authoring-parity-inventory

## Сводка
Проверка показала, что публичный контракт процесса авторинга не покрывает все поля, объявленные в `Process Definition` схеме, и авторинговый пайплайн Materializer/Doctor частично теряет или не валидирует эти поля. Полная parity недостижима с текущим набором источников.

## 1) Ключевые расхождения (high)

### 1.1. Расхождение по top-level полям схемы vs шаблон/материализатор/доки

- В `schemas/process-definition.schema.json` top-level допускаются поля, такие как:
  - `catalog`, `process_pack`, `agent_prompt`, `public_surface`, `required_artifacts`, `required_evidence`, `acceptance`, `input_definitions`, `external_artifacts`, `virtual_artifacts`, `generated_files`, `parameters`, и др. (`schemas/process-definition.schema.json:6-18`, `:29-54`, `:109-126`, `:118-133`).
- Шаблон `templates/process-definition-template.yaml` в этой же области содержит только базовый набор (id/name/version/status/description/stages/roles/artifacts/gates/evolution_policy и т.д.) и эти поля не представленны в шаблоне как first-class (`templates/process-definition-template.yaml:1-178`).
- `tools/processforge.py` не поднимает и/или не материализует эти поля в стандартном пути авторинга:
  - `default_process_authoring_answers` — не инициализирует их (`tools/processforge.py:13148-13248`).
  - `normalize_process_authoring_answers` не нормализует их в обязательную/типовую цепочку (`tools/processforge.py:13151-13295`).
  - `process_from_authoring_answers` формирует output с ограниченным набором полей, где эти поля также отсутствуют (`tools/processforge.py:13516-13532`).
- Документация авторинга описывает основной процесс и выходы prompt/doc/examples, но не раскрывает эти поля как публично доступный контракт (`docs/authoring/process-authoring.md:33-77`).

**Вывод:** публичный интерфейс авторинга не отражает полный top-level контракт, который разрешён схемой.

### 1.2. Расхождение stage-уровня: `required_artifacts`, `required_evidence`, `parameters`, `technical_obligations`

- В схеме стадии они присутствуют (`$defs.stage`), в т.ч. `required_artifacts`, `required_evidence`, `parameters`, `technical_obligations` (`schemas/process-definition.schema.json:266-312`, `:286-309`).
- В материальзации/нормализации по умолчанию:
  - процессный маппинг стадий опирается на ограниченный набор полей (`tools/processforge.py:13417-13495`, `13516-13532`).
- В доке по авторингу перечислены базовые проверки/поля стадий, но не дано целостное API для этих полей (`docs/authoring/process-authoring.md:42-45`, `47-77`).

**Вывод:** schema-level возможности стадии публично не доступны через стандартный authoring-экран/ответы.

### 1.3. Ложное впечатление покрытия через список поддерживаемых полей

- Константа `PROCESS_AUTHORING_SUPPORTED_TOP_LEVEL` включает расширенный набор (`tools/processforge.py:15304-15348`), но это не означает факт реальной передачи в output.
- Реальный builder (`process_from_authoring_answers`) отбрасывает/игнорирует часть полей при сборке процесса (`tools/processforge.py:13516-13532`).

**Вывод:** есть риск “false positive” для parity: поле признаётся в списке поддерживаемых, но не попадает в конечный YAML.

## 2) Граничный контроль Doctor / валидация

- Базовый `validate_process_contract` фокусируется на evolution/coordination/ролях/ссылках и ограниченных правилах стадий (`tools/processforge.py:14225+`).
- Нет явных проверок на полноту покрытия таких public-контрактных полей как `catalog/process_pack/agent_prompt/public_surface` и stage-уровневых `required_evidence/required_artifacts` как обязательной предметной согласованности (`tools/processforge.py:14225-14252`, `14133-14152`).
- `validate_process_definition_files` также не закрывает этот разрыв, проверяя в основном наличие companion-файлов и базовые path-политики (`tools/processforge.py:14133-14152`).

**Вывод:** даже если поле пропущено в materialization, Doctor его не поймает как контрактный дефект.

## 3) Контрольные источники и ограничение области

- В списке файлов отсутствует `docs/concepts/process-authoring.md` (фактически файл не найден; в каталоге есть другие concept-документы), поэтому обязательное требование “сравнить со всеми концепт-источниками” выполнено частично по факту.
- Источник “examples” не представлен среди разрешённых для чтения файлов в этой задаче, поэтому сравнение с примерами неполное (scope ограничен).

## 4) Рекомендуемые точечные решения (без реализации)

1. Зафиксировать explicit parity contract по полям:
   - либо убрать лишние ключи из схематической области authoring-потока, либо расширить template/authoring UI + normalizer + materializer + docs для них.
2. Сделать materializer deterministic: `default/normalize/process_from_authoring_answers` должны поддерживать и пробрасывать один и тот же минимальный контракт для всех public-полей.
3. Усилить doctor-проверки:
   - проверка наличия и корректности top-level полей из каталожного/пакетного/prompt слоя;
   - проверка stage-полей `required_artifacts/required_evidence/technical_obligations/parameters` на соответствие схеме и процессным зависимостям.
4. Восстановить/переименовать отсутствующий ссылочный файл в `docs/concepts/process-authoring.md` или обновить assignment paths, чтобы parity-ревью не зависело от отсутствующего источника.