---
name: local-repos
description: Convention for determining whether a remote repo is already cloned locally before cloning it again.
---

# Local Repos

Before cloning a repository, check whether it is already available locally.

## Check order

1. Look for a directory matching the repo name under common local paths: `~/repo/`, `~/repos/`, `~/src/`, the current working directory.
2. If found, verify it is the correct remote by running `git remote get-url origin` and comparing to the expected URL.
3. If the repo is already cloned and up to date, read files directly — do not clone again.
4. If the repo is not present locally, clone it to a scratchpad directory (per the `scratchpad` rule) before reading.

## Rules

- Prefer reading from an existing local clone over cloning to a temp directory.
- Do not `git pull` or mutate an existing local clone without explicit user instruction.
- When cloning to scratchpad, use a shallow clone (`--depth 1`) unless full history is needed.
