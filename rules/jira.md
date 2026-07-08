---
name: jira
description: How to look up Jira tickets via the Atlassian MCP or Glean fallback.
---

# Jira

## Reading a known ticket

1. Call `getAccessibleAtlassianResources` to retrieve the Atlassian cloud ID.
2. Call `getJiraIssue` with the cloud ID and ticket key (e.g. `PROJ-123`).
3. If the MCP is unavailable, fall back to `Glean read_document` with the ticket URL.

## Searching for tickets

- Use Glean `search` with `app: "jira"` for discovery (e.g. finding tickets by keyword or component).
- Do not guess ticket keys — search first if the key is unknown.

## Creating tickets

- Use the `jira-ticket` skill; do not call `createJiraIssue` directly.
- Only create tickets when the user explicitly asks — do not create them as a side effect of review or research tasks.

## Rules

- Always read before creating to avoid duplicates.
- Ticket summaries and descriptions should be factual and concise — do not include AI disclaimers in ticket bodies.
