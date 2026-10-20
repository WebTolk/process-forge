# Правила выбора обновления

domain-notes: релиз без prerelease новее prerelease с той же числовой частью;
alpha1 < alpha2; alpha.2 < alpha.10; numeric identifiers ниже lexical identifiers;
равный prefix с дополнительным identifier выше короткого. Build metadata не
участвует в precedence. Alphanumeric alpha10 и alpha2 сравниваются лексически
по SemVer, без придуманного natural-sort правила.

domain-model: вход — уже отфильтрованные records выбранного канала; выход —
один прежний record и прежний список warnings. Строки версий не нормализуются
в payload. Штатные ResourceVersionPolicy.key/is_newer и knowledge constraints
остаются побайтно прежними.

domain-rules: numeric/v-prefixed shorthand, отсутствие installed, lexical warning
и tie behavior для равных metadata сохраняются. Исправляется только precedence
допустимых суффиксов при выборе update.
domain-rules-captured: необходимые случаи закрепляются focused pytest без общего
аудита Core. Handoff: architecture-plan определяет локальный tuple key.
