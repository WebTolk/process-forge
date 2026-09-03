# Система обновлений

Система обновлений работает от рабочего места. Она сначала собирает сведения о
серверах обновлений, затем находит кандидатов, подготавливает артефакт,
проверяет его и только после явного подтверждения применяет поддержанное
файловое обновление.

Минимальный сценарий:

```bash
python bin/pf.py update entity-sources rebuild --workplace <workplace>
python bin/pf.py update candidates refresh --workplace <workplace>
python bin/pf.py update candidates list --workplace <workplace>
python bin/pf.py update notifications list --workplace <workplace>
python bin/pf.py update changelog show --workplace <workplace> --candidate <candidate-id>
python bin/pf.py update stage --workplace <workplace> --candidate <candidate-id>
python bin/pf.py update verify --workplace <workplace> --candidate <candidate-id>
python bin/pf.py update apply --workplace <workplace> --candidate <candidate-id> --confirm
python bin/pf.py update rollback --workplace <workplace> --candidate <candidate-id>
```

Для воспроизводимых локальных проверок используйте `manifest_url` и артефакты с
URL вида `file:///...`. Для настоящего удалённого сервера обновлений используйте
HTTPS, `sha256` и ручное подтверждение оператора перед применением.

## Как обновлять установленное ядро ProcessForge

Не распаковывайте новый релиз в проектную `.pf`. Обновляется установленный
дистрибутив ProcessForge, а рабочие места и проекты остаются отдельно.

### Первый управляемый переход с 1.0.2 на 1.1.0

В публичном дистрибутиве 1.0.2 ещё нет manifest-based core updater. Для этого
единственного перехода распакуйте архив 1.1.0 во временную staging-папку и
запустите новый updater оттуда против стабильного пути установленного Core.

1. Сделайте резервную копию установленного Core и остановите optional
   long-lived PF Runtime.
2. Распакуйте `processforge-1.1.0.zip` в `<staged-processforge-1.1.0>`.
3. Проверьте staging-дистрибутив:

   ```powershell
   python <staged-processforge-1.1.0>/bin/pf.py version
   python <staged-processforge-1.1.0>/bin/pf.py release-test --root <staged-processforge-1.1.0> --public
   ```

4. Постройте план и явно примените обновление к стабильной установленной папке:

   ```powershell
   python <staged-processforge-1.1.0>/bin/pf.py core-update plan --core-root <installed-processforge> --archive <processforge-1.1.0.zip>
   python <staged-processforge-1.1.0>/bin/pf.py core-update apply --core-root <installed-processforge> --archive <processforge-1.1.0.zip> --confirm
   ```

5. Проверьте установленный Core и workplace, затем перезапустите PF Runtime,
   если он настроен:

   ```powershell
   python <installed-processforge>/bin/pf.py version
   python <installed-processforge>/bin/pf.py core-update status --core-root <installed-processforge>
   python <installed-processforge>/bin/pf.py doctor-workplace --root <workplace>
   ```

6. Для каждого связанного проекта выполните `project-upgrade-check`, обновите
   context и запустите `doctor-project` через установленный CLI 1.1.0.

Updater заранее пишет backups и operation journal. При прерванном обновлении
используйте `core-update status` и `core-update repair`. Следующие релизы смогут
использовать updater, уже установленный в составе 1.1.0.

## Как обновлять проектную `.pf`

Проектная `.pf` не обновляется наложением архива ProcessForge. Команда
`project-upgrade-check` создаёт отчёт оценки под `.pf/artifacts/` и не изменяет
проектные файлы автоматически:

```bash
python bin/pf.py project-upgrade-check --project-root <project>
```

После отчёта:

1. Прочитайте результат оценки и migration guide для целевой версии.
2. Если миграция не требуется, обновите снимок контекста:

   ```bash
   python bin/pf.py project-context-refresh --project-root <project>
   python bin/pf.py project-context-check --project-root <project>
   python bin/pf.py doctor-project --project-root <project>
   ```

3. Если отчёт требует изменений в проектной `.pf`, внесите их явно через
   соответствующий процесс или команду ProcessForge, затем снова выполните
   `project-context-refresh`, `project-context-check` и `doctor-project`.

Для ProcessForge `1.1.0` обязательная миграция проектных `.pf` не требуется.
Существующие assignments и capsules остаются валидными. Обновите project
context и search indexes, чтобы Garage, MCP и Runtime использовали актуальные
resource snapshots.
