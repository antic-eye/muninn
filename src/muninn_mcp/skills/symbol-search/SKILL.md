---
name: symbol-search
description: "Use when searching for where a symbol is defined, before grepping. Also use when opening source files to index their symbols for future searches."
---

# Symbol Search — Muninn

## Overview

Muninn maintains a semantic symbol index per project. The AI populates it on-demand as
it reads source files, and queries it with natural language instead of grepping.

## When to Index

Index symbols whenever you open a source file for reading or editing:

```
symbol_index([
  {"name": "MyClass", "kind": "class", "file": "models/user.py", "line": 10,
   "signature": "class MyClass(Base)", "docstring": "Represents a user."},
  {"name": "save", "kind": "method", "file": "models/user.py", "line": 25,
   "signature": "def save(self) -> None", "docstring": "Persist to DB."},
])
```

Index **after creating** a new file.

Call `symbol_delete_file(old_path)` **before renaming or deleting** a file, then
re-index the new path if applicable.

## What Counts as a Symbol

**DO index:**
- Top-level functions and async functions
- Classes and their methods
- Module-level constants (`UPPER_CASE`)
- Interfaces, protocols, abstract base classes
- Type aliases (`UserId = str`)

**Do NOT index:**
- Local variables inside functions
- Loop variables
- Import aliases (`from x import y as z` — skip `z`)

## When to Search

Search instead of grep whenever you need to find a symbol:

```
symbol_search("function that validates JWT tokens")
symbol_search("class for user repository pattern")
symbol_search("all classes in auth module")
```

**Use `symbol_search` BEFORE reaching for grep or glob.** It is faster and understands
intent — you can describe what the symbol does, not just its exact name.

## Symbol Kinds

Use one of: `function`, `class`, `method`, `variable`, `constant`, `interface`, `type`

## Output Format

`symbol_search` returns Markdown with kind, name, file:line, relevance score, and
signature/docstring. Navigate directly to the file:line shown.

## Maintenance

- After a large refactor affecting many files, wipe and re-index: `symbol_wipe(confirm=True)` then re-open files.
- If results seem stale or wrong for a file, call `symbol_delete_file(file)` then re-index.
