# Rules

Shared rules referenced by plugins and agents. A rule defines a reusable convention or workflow that multiple plugins depend on — keeping it here avoids duplication and drift.

## Index

| Rule | Description |
|------|-------------|
| [pr-disclaimers](./pr-disclaimers.md) | Disclaimer text appended to every agent-posted PR comment |
| [pr-review-principles](./pr-review-principles.md) | Three-outcome review logic and finding classification (blocking, label) |
| [scratchpad](./scratchpad.md) | Convention for naming and creating temporary working directories |
| [local-repos](./local-repos.md) | How to check for an existing local clone before cloning again |
| [search](./search.md) | Tool order and narrowing strategy for local codebase searches |
| [jira](./jira.md) | Reading and searching Jira tickets via Atlassian MCP or Glean fallback |

## Usage

Reference a rule from an agent or skill with backtick notation:

```
Follow the `scratchpad` rule when creating working directories.
```

Rules are resolved by name — the file must exist here as `<name>.md`.
