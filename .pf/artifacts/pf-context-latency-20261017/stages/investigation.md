# Путь контекста

Актуальный contextfresh/continue, sessionabsent. MCP handler строит ProjectContextService.context, затем отдельно snapshot иProcessExecutionService.state безточных selectors. ProjectContextService.context вызывает freshness,snapshot,metadata,searchreadiness,mode,worksummary,process/resource summaries,derivedreports иboundary.

Гипотезы: дорогая общая Work-summary, automatic current Work selection, repeatedfreshness/indexprocessing илифайловыеоперации. Быстрыйexact Work0.053с имедленныйcontext14.675с ещё не определяют виновную функцию. Дальше измерение.
