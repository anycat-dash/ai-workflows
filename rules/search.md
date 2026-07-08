---
name: search
description: Workflow for searching a local codebase — tool order, narrowing strategy, and when to stop.
---

# Search

Use this workflow when locating symbols, patterns, or files in a local repository.

## Tool order

1. **`Grep`** — for exact strings, symbol names, or regex patterns across the repo.
2. **`Glob`** — for finding files by name or path pattern when you know the structure.
3. **`Bash` (`find`, `rg`)** — for more complex filters (file type + pattern, directory exclusions, etc.).
4. **`Read`** — once you have a candidate file, read the relevant section.

## Narrowing strategy

- Start with the most specific pattern possible; broaden only if no results.
- Exclude noise directories upfront: `node_modules/`, `vendor/`, `.git/`, `dist/`, `build/`, `__pycache__/`.
- If a symbol search returns too many results, add a path filter to narrow to the most likely directory.

## When to stop

- Stop after finding the first definitive match for lookup tasks.
- For "find all call sites" tasks, exhaust results before reporting.
- If after three attempts no match is found, report that and suggest the user verify the symbol name or path.
