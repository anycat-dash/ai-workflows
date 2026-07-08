---
name: scratchpad
description: Convention for creating and naming temporary working directories under ~/scratchpad/.
---

# Scratchpad

Use `~/scratchpad/` for all temporary working directories created during agent tasks.

## Naming convention

```
~/scratchpad/YYYY-MM-DD-{identifier}/
```

- `YYYY-MM-DD` — today's date
- `{identifier}` — a filesystem-safe slug describing the task (lowercase, hyphens only, no spaces or slashes; replace `/` with `-`)

**Examples:**
- `~/scratchpad/2026-07-07-my-repo-pr123/`
- `~/scratchpad/2026-07-07-my-repo-cve-diff/`
- `~/scratchpad/2026-07-07-auth-service-security-audit/`

## Rules

- Create the directory if it does not exist before writing any files.
- Use relative paths for all file operations once inside the directory.
- For monorepos with multiple sub-projects, use one folder per project or a shared folder with project-prefixed filenames.
- Do not write to `~/scratchpad/` directly — always create a named subdirectory.
