# T08 — наблюдения для следующих Work

Result: captured; project-local proposals only, без автоматических глобальных правок.

1. **T01: границы identity.** Различать source commit, archive bytes, installed
   ownership manifest и загруженный MCP process. Одинаковый VERSION и даже
   classifier SHA256 не гарантируют равенство classification provenance.
   Evidence: investigation.md, host-process-identity.json, final-verification.json.
2. **T01/T02: readiness и выбранные ресурсы.** Global index ready и 85 документов
   не означают, что разрешённые текущему проекту ресурсы входят в индекс.
   Зафиксировать семантику пересечения grants/catalogue и доступной навигации;
   unresolved template target не должен считаться проверенной навигацией.
   Evidence: search-catalogue-diagnosis.json, fixture-resolve-template.json,
   fixture-search-positive.json. Отдельное улучшение контракта, не скрытый T08 patch.
3. **T06/T09: воспроизводимая приёмка.** Сохранять actual-host lifecycle отдельно
   от subprocess regression и reconnect. Request IDs показывать только там,
   где клиент предоставляет их; не выдумывать host transport IDs. Проверять
   notification silence, stderr/stdout boundary и genuine stale guards.
   Evidence: reconnect-proof.json, fixture-stale-search.json, installed regressions.
4. **Операторский backlog.** Отдельно диагностировать missing manifest чужого
   зарегистрированного проекта и старый unresolved template registry target.
   Никаких автоматических repairs или registry removals в T08.

Scope promotion: none. Public documentation, process definition, host hooks и
shared configuration не изменялись. Порядок плана r02 сохраняется: после закрытия
T08 следующая самостоятельная Work — T01, затем T09. Текущий запрос завершает T08.
