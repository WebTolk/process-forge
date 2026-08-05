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

Для воспроизводимых локальных проверок используйте
`provider: processforge_json_file` и URL вида `file:///...`. Для настоящего
удалённого сервера обновлений используйте `provider: processforge_json`, HTTPS,
`sha256` и ручное подтверждение оператора перед применением.

## Как обновлять установленное ядро ProcessForge

Не распаковывайте новый релиз в проектную `.pf`. Обновляется установленный
дистрибутив ProcessForge, а рабочие места и проекты остаются отдельно.

Рекомендуемый ручной порядок:

1. Распакуйте `processforge.zip` в новую версионную папку вне проекта,
   например `<processforge-root-1.0.1>`.
2. Проверьте новый дистрибутив:

   ```powershell
   python <processforge-root-1.0.1>/bin/pf.py version
   python <processforge-root-1.0.1>/bin/pf.py release-test --root <processforge-root-1.0.1> --public
   ```

3. В `<workplace>/registries/distributions.yaml` обновите запись
   `processforge`: путь должен указывать на новую папку, версия - на новую
   версию релиза.
4. Проверьте рабочее место:

   ```powershell
   python <processforge-root-1.0.1>/bin/pf.py doctor-workplace --workplace <workplace>
   ```

5. Для каждого связанного проекта выполните проверку и обновление снимка
   контекста:

   ```powershell
   python <processforge-root-1.0.1>/bin/pf.py project-upgrade-check --project-root <project>
   python <processforge-root-1.0.1>/bin/pf.py project-context-refresh --project-root <project>
   python <processforge-root-1.0.1>/bin/pf.py project-context-check --project-root <project>
   python <processforge-root-1.0.1>/bin/pf.py doctor-project --project-root <project>
   ```

Старую папку дистрибутива держите до успешной проверки. Для отката верните путь
в `registries/distributions.yaml` на предыдущую версию и снова выполните
`doctor-workplace` и проверки проектов.

Распаковка поверх старой папки допустима только как ручной аварийный вариант
после резервной копии. Она хуже контролируется: файлы, удалённые из нового
релиза, могут остаться от старой версии.

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

Для ProcessForge `1.0.1` миграция проектных `.pf` не требуется. Старые
assignments и capsules остаются валидными; новые shell-agent flows могут
использовать `workspace_access`, чтобы получать общие знания, шаблоны,
инструменты и MCP через приватный runtime-файл.
