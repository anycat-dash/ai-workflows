---
name: fresh-eyes
description: Spawn a `reviewer` subagent to give unbiased feedback on uncommitted local changes (git diff HEAD), or the most recent commit when the working tree is clean. No PR posting.
---

When the user invokes `/fresh-eyes` (or asks you to run this command):

1. **Gather the diff.** Run `git diff HEAD` to get all uncommitted changes. If the working tree is clean, check whether `HEAD~1` exists (`git rev-parse --verify HEAD~1`); if it does, run `git diff HEAD~1` and tell the user you are reviewing the most recent commit; if it does not (single-commit repo), tell the user there is nothing to review and stop.

2. **Check scope.** Run `git status` to see which files are affected. If the diff is very large, summarize the file list to the user and ask if they want to narrow the scope before proceeding.

3. **Delegate to the `reviewer` subagent.** Spawn the `reviewer` subagent with the diff as its primary context. Instruct it to treat this as an ad-hoc code review (no PR URL, no posting to GitHub) using the same classification as PR review: each finding must have a `blocking` boolean and a [Conventional Comments](https://conventionalcomments.org) `label` (see the `pr-review-principles` rule).

4. **Report findings.** Present the `reviewer` subagent's output directly. Do not post anything to GitHub. If there are no findings, say so explicitly.
