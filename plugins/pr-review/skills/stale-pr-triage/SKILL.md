---
name: stale-pr-triage
description: Triage stale or old pull requests to determine if they should be closed, reimplemented, or merged. Use when the user shares a PR URL and asks whether it is still relevant or should be closed.
---

Evaluate whether an old or stale pull request still solves a real problem, or whether it should be closed. Uses a sequential pipeline: fetch the PR, compare its changes to the current codebase, optionally investigate broader context, then present a disposition recommendation to the user.

## Trigger

Triaging a stale, old, or abandoned PR for relevance. Not for reviewing active PRs (use `pr-review` skill) or processing Dependabot updates (use `dependabot-resolve` skill).

## Workflow Overview

```
- [ ] Phase 1: Preflight (fetch PR metadata and diff)
- [ ] Phase 2: Current state comparison
- [ ] Phase 3: Broader context (conditional)
- [ ] Phase 4: Disposition summary (safety gate)
- [ ] Phase 5: Execute close (conditional, after user approval)
```

## Phase 1: Preflight

**Entry:** User provided a PR URL; owner, repo, and PR number can be parsed.

Parse the PR URL to extract owner, repo, and PR number. Then fetch in parallel:

```bash
gh pr view <number> -R <owner>/<repo> --json title,body,state,author,createdAt,updatedAt,baseRefName,headRefName,additions,deletions,changedFiles,labels

gh pr diff <number> -R <owner>/<repo>

gh pr view <number> -R <owner>/<repo> --json commits --jq '.commits[] | "\(.oid[:8]) \(.messageHeadline)"'
```

**Exit criteria:** PR metadata, diff, and commit list are in hand. If the PR is already closed or merged, report that and stop.

## Phase 2: Current state comparison

**Entry:** Phase 1 complete; PR metadata, diff, and commit list are available.

For each file touched by the PR diff:

1. **Check current state on base branch.** If the repo is cloned locally (per the `local-repos` rule), read the file directly. Otherwise clone it first.
2. **Check git log for the file on the base branch** to see whether changes landed through other commits since the PR was opened.
3. **Classify each change** in the diff into one of:
   - **Applied**: the exact change (or equivalent) is already on the base branch
   - **Superseded**: the problem was solved differently on the base branch
   - **Still needed**: the change addresses something not yet fixed
   - **Obsolete**: the file, feature, or code path was removed entirely

Keep the per-file classification concise. Do not read every file in the repo; only read files that appear in the diff.

**Exit criteria:** A per-file classification. If all changes are applied or superseded, recommend "close" and skip Phase 3. If any changes are "still needed" or "obsolete," proceed to Phase 3.

## Phase 3: Broader context (conditional)

**Entry:** Phase 2 found at least one "still needed" or "obsolete" change.

The goal is to determine whether the problem the PR was solving is still relevant.

Investigate in order, stopping once you have enough signal:

1. **Project/directory health.** For the directories touched by the PR, check:
   - Last non-automated commit (exclude Go/Alpine bumps, copyright headers, dependency updates)
   - Ownership signals: `service.yml` (teamName, Slack channel, PagerDuty), `.codeowners`
   - Whether the project is listed in any deprecation or removal tracking
2. **Glean search.** Query for the project, feature, or system the PR targets. Look for deprecation signals, migration decisions, or replacement systems. Use `chat` for broad questions, `search` for specific documents.
3. **Active deployment.** If the PR targets a deployable service, check whether it has an owner, active deployments, or recent non-automated changes.

**Exit criteria:** A context summary answering: "Does the problem this PR solves still matter?"

## Phase 4: Disposition summary

**Entry:** Phases 1-3 complete (or Phase 3 skipped per Phase 2 exit criteria); classification and context summary are available.

Present findings to the user with one of four recommendations:

| Disposition | When to use |
|---|---|
| **Close** | Problem is solved or no longer relevant. The fix landed another way, or the target system is deprecated. |
| **Close and track** | Problem is real but the branch is too stale to salvage. Recommend creating a Jira ticket for reimplementation. |
| **Rebase and merge** | Changes are still needed and the diff is small/clean enough to rebase onto the current base branch. |
| **Needs deeper review** | Changes are still needed but the scope or risk requires a full PR review. Hand off to the `pr-review` skill. |

The summary must include:

- PR title and age (how long it has been open)
- What the PR was trying to solve
- Whether the fix landed another way (with commit references if applicable)
- Whether the target system/project is still active
- The recommended disposition with reasoning

**Do not close, comment on, or modify the PR until the user decides.** This is a safety gate; the user controls the action.

When the disposition is **Close** or **Close and track**, draft a closing comment alongside the summary. Present it to the user in this format:

```
**Draft closing comment (will be posted to the PR):**

[comment text]

---

Close this PR with the comment above? (yes/no)
```

The closing comment should be concise and explain why the PR is being closed (e.g., "changes already landed via [commit], target system deprecated, problem no longer relevant"). It must end with the disclaimer from the `pr-disclaimers` rule.

If the user approves, proceed to Phase 5. If the user declines or chooses a different disposition, stop.

## Phase 5: Execute close (conditional)

**Entry:** User approved the closing comment from Phase 4.

1. Write the closing comment to a file in the scratchpad (e.g., `~/scratchpad/YYYY-MM-DD-<repo>-pr<number>/close-comment.md`).
2. Post the comment and close the PR:

```bash
gh pr comment <number> -R <owner>/<repo> --body-file <path-to-comment>
gh pr close <number> -R <owner>/<repo>
```

3. Confirm to the user that the PR was closed.

**Exit criteria:** PR is closed with the comment posted.

## Scope boundaries

- **Single PR only.** Batch triage (e.g., "triage all PRs older than 1 year") is out of scope for this skill.
- **No subagents.** The phases are sequential and tool calls are bounded per PR.
