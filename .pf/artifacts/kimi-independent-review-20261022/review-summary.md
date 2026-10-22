# Независимое ревью Kimi: результат и первый вход в PF

Проверен commit `265767d986ba6dd57af5ecb74e298f7156cb9c32`. Вердикт: **fail / NO-GO для приёмки Kimi-интеграции**. Код продукта не исправлялся.

Подтверждены следующие замечания:

1. **P1:** `tools/pf_runtime/kimi_hooks.py:113` использует `tool_use_id`, тогда как Kimi Code 2.3.0 передаёт `tool_call_id`. Два различных raw payload дают одно нормализованное событие.
2. **P1:** `kimi_hooks.py:150` принимает prompt только как строку. Реальный массив text parts даёт ноль записей переписки, строковый контроль — одну.
3. **P2:** `kimi_hooks.py:171` ожидает `last_assistant_message`/`agent_id`; реальный SubagentStop использует `response`/`agent_name`. Ответ теряется. Полное assistant capture из Stop/SessionEnd также не обосновано контрактом host.
4. **P1:** KimiHooksPolicy добавлена в source registry, но отсутствует в фактически исполняемой installed-среде. Изолированная проверка точного installed registry даёт `adapter_untrusted`. Live host acceptance не выполнен; session enrollment для trusted hooks в PF уже существует.
5. **P1:** семь исторических immutable capsules изменены в Git только переводами строк CRLF -> LF. Parent/live bytes совпадают с pins, commit blobs — нет. Текущие live capsules целы; восстановление доставленного Git-снимка нарушает byte-hash checks.
6. **P2:** общий PASS в audit шире доказательств: Ruff проходит, mypy на трёх проверяемых файлах остаётся с exit 1 и двумя Logger diagnostics. Прежние Codex/fixture tests и PF process outbox не квалифицируют Kimi hooks.

Шесть изолированных probes подтвердили пять дефектных состояний и существующую поддержку evidence-file arrays. Существующий provider-admission smoke прошёл. Это доказательства ревью, а не принятие неисправного Kimi-кандидата. Проверки и изменения не затрагивали действующие сервисы или чужие рабочие файлы.

Evolve-отчёт Kimi полезен как наблюдение первого входа без памяти. Подтверждается нагрузка полного девятистадийного процесса и недостаток готовых примеров scope/evidence. Требуют поправки утверждения об отсутствующих session enrollment, evidence arrays и templates. Ограничения Glob/вывода/оболочки сами по себе не доказывают поломку PF.

Сравнение источников знаний:

| Источник | Что даёт агенту |
| --- | --- |
| PF напрямую | Текущее состояние, scope, immutable capsule, стадия, requirements, разрешённые ресурсы и provenance |
| Память агента | Историческую навигацию и привычки проверки; не текущие права и не приёмку |
| Общие знания | Методы анализа Python/Git, гипотезы о контрактах и план воспроизведения; конкретные факты требуют проверки |

В текущем ревью опытному агенту также пришлось читать source для допустимого execution_mode и искать образец gate evidence. Успех такого агента не доказывает самодостаточность первого входа. Подробная проверка evolve: [first-use-assessment.md](first-use-assessment.md).
