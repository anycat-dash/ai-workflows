---
name: pr-review-principles
description: Three-outcome review logic and finding classification used across all PR review agents and skills.
---

# PR Review Principles

## Finding classification

Every finding has two orthogonal fields:

| Field | Type | Description |
|-------|------|-------------|
| `blocking` | boolean | Whether the finding should block merge |
| `label` | string | [Conventional Comments](https://conventionalcomments.org) label |

**`blocking: true`** — security issues, correctness bugs, data integrity risks, breaking changes.  
**`blocking: false`** — quality feedback, style, docs, naming, non-critical improvements.

Valid labels: `issue`, `suggestion`, `nitpick`, `question`, `thought`, `todo`, `chore`, `praise`, `note`, `typo`, `polish`, `quibble`.

## Three-outcome recommendation logic

| Outcome | Mechanism | Condition |
|---------|-----------|-----------|
| **Hard block** | `REQUEST_CHANGES` | Any finding has `blocking: true` |
| **Soft block** | `COMMENT` | No blocking findings, but one or more findings with label in `{issue, todo, question, chore}` |
| **Approve** | `COMMENT` | No blocking findings and no soft-block labels |

- Base the recommendation on **all findings**, including those already raised by other reviewers.
- If a blocking finding exists on the PR (even if filtered from your output), you must request changes.
- Do not include the recommendation text in the posted comment body — only in the GitHub review decision.
