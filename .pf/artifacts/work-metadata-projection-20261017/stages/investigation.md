# Investigation and impact

Inspected current CurrentWorkService/YamlWorkRecordReader, catalog and selector, ProcessExecutionService dependency fields, composition factories and pf.context handler. Full selected record methods and exact canonical path must remain unchanged. Existing WorkInventory supplies sorted paths. Baseline source captured from Git f3fecf7 into own scratch; no unrelated .pf state copied or changed.

Existing checks before edits: work_record_read_composition 23 tests + 128 original comparisons, core_read_composition 20 tests, work_selection_service 14 scenarios + 53 canonical cases; all exit 0. The retained original catalog and methods support post-change differential proof.

Discovery semantics: summary has OR activity, fallback/empty/bootstrap rows; catalog has AND activity plus pending intent, validated ids/ownership and historical queries. Missing/null/false values and even a nonempty document with none of the selected fields must preserve truthiness. Literal top-level projection {} therefore requires native full fallback for such unusual forms.

Read ordering matters: enumerate paths lazily, read each Run and then its assignments in the consumer's original order. An eager load of all Run bodies could expose a later error before an earlier assignment failure. Keep custom full record/doc seams, native paths, known tests and error propagation. Completion journals require full native inputs only when present; raw id must not be replaced with path fallback.

Impact bounded to shared Work read pass, factories and MCP assembly; external payloads and schemas unchanged. YAML remains authoritative. Source baseline/differential helper retained in .pf/tmp/work-metadata-projection-20261017. Investigation complete, impact understood.
