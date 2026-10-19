# Verified PF Python material for this source refactor

These are task-selected excerpts from fulltext material already resolved through the current source CLI in the exact primary Work. They are complete declared project inputs for successors; no metadata-only or external-directory grant is inferred. No MCP connection is required.

## docs.python:root / simple-statements.md

Document sha256:c93902a569c34ad1882aeb6e6fc399feb1ecdcf1aa7abc071efce674d8b669a1; lines 454-480.

`importlib.import_module()` (https://docs.python.org/3/library/importlib.html#importlib.import_module) is provided to support applications that determine dynamically the modules to be loaded.

Raises an auditing event (https://docs.python.org/3/library/sys.html#auditing)`import` with arguments `module`, `filename`, `sys.path`, `sys.meta_path`, `sys.path_hooks`.

7.11.1. Future statements¶ (https://docs.python.org/3/reference/simple_stmts.html#future-statements)

A *future statement* is a directive to the compiler that a particular module should be compiled using syntax or semantics that will be available in a specified future release of Python where the feature becomes standard.

The future statement is intended to ease migration to future versions of Python that introduce incompatible changes to the language. It allows use of the new features on a per-module basis before the release in which the feature becomes standard.

**future_stmt**: "from" "__future__" "import" feature (https://docs.python.org/3/reference/simple_stmts.html#grammar-token-python-grammar-feature) ["as" identifier (https://docs.python.org/3/reference/lexical_analysis.html#grammar-token-python-grammar-identifier)]
             ("," feature (https://docs.python.org/3/reference/simple_stmts.html#grammar-token-python-grammar-feature) ["as" identifier (https://docs.python.org/3/reference/lexical_analysis.html#grammar-token-python-grammar-identifier)])*
             | "from" "__future__" "import" "(" feature (https://docs.python.org/3/reference/simple_stmts.html#grammar-token-python-grammar-feature) ["as" identifier (https://docs.python.org/3/reference/lexical_analysis.html#grammar-token-python-grammar-identifier)]
             ("," feature (https://docs.python.org/3/reference/simple_stmts.html#grammar-token-python-grammar-feature) ["as" identifier (https://docs.python.org/3/reference/lexical_analysis.html#grammar-token-python-grammar-identifier)])* [","] ")"
**feature**:     identifier (https://docs.python.org/3/reference/lexical_analysis.html#grammar-token-python-grammar-identifier)

```

A future statement must appear near the top of the module. The only lines that can appear before a future statement are:

the module docstring (if any),

comments,

blank lines, and

other future statements.

## docs.python-practices:root / pep20.md

Document sha256:9ee7c54f484c758a2e59d242d66326ec7f198de5eadbdf017eaefcf090718d5a; lines 39-57.

Beautiful is better than ugly.
Explicit is better than implicit.
Simple is better than complex.
Complex is better than complicated.
Flat is better than nested.
Sparse is better than dense.
Readability counts.
Special cases aren't special enough to break the rules.
Although practicality beats purity.
Errors should never pass silently.
Unless explicitly silenced.
In the face of ambiguity, refuse the temptation to guess.
There should be one-- and preferably only one --obvious way to do it.
Although that way may not be obvious at first unless you're Dutch.
Now is better than never.
Although never is often better than *right* now.
If the implementation is hard to explain, it's a bad idea.
If the implementation is easy to explain, it may be a good idea.
Namespaces are one honking great idea -- let's do more of those!
