# Повторная проверка Kimi

Исправлен hook adapter для контракта Kimi Code 2.3.0. Это не новый PF runtime-driver. Исходные отчёты Kimi и независимое ревью сохранены; результаты исправленного кандидата находятся в новых test-report/code-quality-report.

## Перед живым прогоном

1. Исполняемая установка PF должна содержать исправленные kimi_hooks.py, kimi_adapters.py и регистрацию KimiHooksPolicy в builtin_provider_adapters.py. Наличие новых файлов только в checkout этого не подтверждает. Проверенная ранее установленная копия не содержит регистрации и возвращает adapter_untrusted. В этой задаче установка и Runtime/MCP не обновлялись и не перезапускались.
2. При отдельном штатном обновлении проверить источник/версию реально исполняемого Runtime и его adapter registry, затем запускать свежую Kimi session. Не обходить denied через локальный fallback и не регистрировать выдуманный session id вручную.
3. Проверить подписки Kimi на SessionStart, SessionEnd, PreToolUse, PostToolUse, PostToolUseFailure, UserPromptSubmit, PreCompact, PostCompact, Stop, SubagentStop. Ранее PostToolUseFailure не был подписан. Конфигурация host в этой задаче не менялась.
4. Ранее hook timeout был 3 секунды, а существующий PF Runtime request использует timeout 5 секунд плюс запуск Python. Для повторной квалификации задать достаточный hook timeout, например 10 секунд, в рамках отдельной настройки host. Этот отчёт сам не разрешает инфраструктурные изменения.
5. При необходимости включить PF_KIMI_HOOK_DEBUG=1 для stderr diagnostics. Script всегда остаётся наблюдателем: ошибка доставки не блокирует Kimi; успешный exit code не доказывает приёмку события.

## Сценарии

- Начать новую сессию и проверить автоматическую регистрацию настоящего session_id.
- Отправить два разных текстовых сообщения: оба должны появиться в private chat transcript.
- Выполнить два разных вызова инструмента: должны быть два raw receipt и два normalized events. Повторная доставка того же payload не создаёт дублей.
- Проверить успешный и неуспешный вызов; неуспешный завершается событием с status=failed, без копирования tool input/output/error text в публичные event metadata.
- Завершить субагента: в transcript должны быть его native response summary и participant subagent:<agent_name>.
- Завершить сессию: должен появиться session-ended effect. Подменённые derived fields должны отвергаться.

## Честные ограничения

Stop и SessionEnd в этом контракте не передают текст основного ответа Kimi. Адаптер его не выдумывает и не читает посторонние файлы сессий. Non-text parts сохраняются только существующим private raw journal при включённой записи; в transcript попадает поддерживаемый текст. Идентичные ID-less payload без native occurrence id невозможно отличить от повторной доставки; они сохраняют idempotent effect. SessionStart не получает вымышленный Codex additionalContext — Kimi этот результат не использует.

Успешные source fixtures и проверки качества не являются доказательством actual connected-host acceptance. После живого прогона сохранить отдельно native payload shapes, installed/runtime provenance, настоящие session ids, receipts/events/chat ids и итоговый вердикт.
