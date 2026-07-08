---
name: pr-review
description: Review pull requests with structured analysis and line-level comments. Use when the user shares a PR URL or asks to review a PR or code changes.
---

Review pull requests with thorough analysis and post well-formatted review comments. See the `pr-disclaimers` rule for disclaimer requirements.

## Principles

- **Default to deep review.** You must not rely only on the diff. You must read full context for changed code, trace call sites and usages, check tests, and assess cross-file impact. Shallow diff-only reviews miss breaking changes and untested behavior.
- **Verify reproducible findings before surfacing them.** Findings that assert a code defect (correctness bugs, security vulnerabilities, data-integrity risks, breaking changes) must be confirmed by a per-finding verification pass that reproduces the defect, for code bugs with a minimal failing test run in an isolated worktree. Drop findings that prove to be false positives; the goal is to never surface a bug that turns out to behave correctly.
- **Use Jira context when available.** When a PR links to a Jira ticket, you must fetch and use the ticket summary and description to understand the goal and acceptance criteria. Many PRs omit full context in the description; the linked ticket provides the intended change.
- **Filter duplicate feedback.** You must not post comments on issues already raised by other reviewers or bots. You must check existing review comments and exclude findings that are already covered. Filtering only affects which comments you post, not your approval decision.
- **Resolve line numbers from local files.** You must use the local repo checkout and a line-numbering CLI (e.g. `cat -n`) to get line numbers. You must not derive line numbers from the GitHub diff or preview blobs. Line numbers must match the file on disk and GitHub's PR view.
- **Use line-level comments only for code-specific feedback.** You must attach line-level comments only to feedback that directly relates to the code on that specific line. You must use the summary comment for PR-level observations (missing ticket, process concerns, general approach).
- **Base recommendation on full findings, not filtered comments.** When deciding whether to request changes or comment, you must consider all findings including those already raised by others. If a blocking finding exists on the PR (even if you filtered it out), you must request changes until it is fixed.
- **Use three recommendation outcomes based on findings.** Hard block (REQUEST_CHANGES): any finding has `blocking: true` (security issues, bugs, breaking changes); recommend the user not approve. Soft block (COMMENT): no blocking findings, but non-blocking `issue`, `todo`, `question`, or `chore` findings exist that should be addressed before approval; recommend the user withhold approval. Recommend approval (COMMENT): no findings with labels in the soft-block set (`issue`, `todo`, `question`, `chore`) or with `blocking: true`; recommend the user approve. Do not include the recommendation in the posted comment body (see the Comment format and approval section below).
- **Classify findings with blocking + label.** Every finding has two orthogonal fields: `blocking` (boolean, whether it should block merge) and `label` (a [Conventional Comments](https://conventionalcomments.org) label: `issue`, `suggestion`, `nitpick`, `question`, `thought`, `todo`, `chore`, `praise`, `note`, `typo`, `polish`, `quibble`). Use `blocking: true` for security issues, correctness bugs, data integrity risks, and breaking changes. Use `blocking: false` for quality feedback, style, docs, naming, and non-critical improvements.
- **Verify the changelog YAML bump type matches the actual changes.** Assess whether the declared `change_level` is correct for the scope of changes. Flag manual version field or changelog file edits as an `issue` with `blocking: true`.
- **Flag a missing changelog YAML block as a hard block.** A missing changelog YAML block is an `issue` finding with `blocking: true`. CI depends on it to determine the version bump type.

## Comment format and approval

- **You must keep PR review comments short and actionable.** Focus only on issues, questions, and recommendations for the PR author. Do not summarize what the code does, do not explain implementation details the author already wrote, and do not reiterate what the PR description already explains. Lead with problems or concerns. If there are no issues, state that briefly (e.g., "No issues found" or "Looks good").
- **You must use the Conventional Comments format for line-level comments.** Each line-level comment must use the format `{label} [{qualifier}]: {subject}` followed by the discussion body. Use labels from the [Conventional Comments](https://conventionalcomments.org) spec: `issue`, `suggestion`, `nitpick`, `question`, `thought`, `todo`, `chore`, `praise`, `note`, `typo`, `polish`, `quibble`. The qualifier is optional: add `(blocking)` for hard blocks (must fix before merge), omit the qualifier for soft blocks (should fix before approval), or add `(non-blocking)` for optional feedback.
- **Review comments are for the PR author, not for the requesting reviewer.** Do not include meta-commentary like "Recommendation: Ready for approval" or "Wait for CI" in the posted comment. These are for your internal recommendation to the user, not for the author. The comment body should only contain feedback about the code.
- **You must get user approval before posting PR review comments.** Show the draft comment to the user and wait for explicit approval before calling any tool that posts to GitHub (`gh pr review`, `gh pr comment`, `gh issue comment` on PRs). Exception: Line-level comments with pre-approved specific content (e.g., "leave a comment on line 123 saying X") do not require separate approval.

## Workflow

The workflow is **local-centric**: use the local repo and local git for file lists and diffs. Use `gh` (GitHub CLI) only for small reads: PR metadata and existing review comments.

| Phase | Description |
|-------|-------------|
| 1 | Preflight: parse input, fetch metadata, checkout, gather comments, categorize changes |
| 2 | Research: Jira + Glean context, update pr-details.json |
| 3 | Review: spawn the lenses listed in `categorization.lensesToRun` (or analyze them inline) |
| 4 | Consolidate (dedup), verify code-bug findings via per-finding subagents, confirm soft findings inline |
| 5 | Draft review and get user approval |
| 6 | Post review |

## Phase 1: Preflight

Run `pr-review-preflight.py`. It handles URL/repo parsing, metadata fetch, worktree creation, and review comment collection in a single call:

```bash
# From a PR URL
pr-review-preflight.py https://github.com/org/repo/pull/123

# From repo + PR number
pr-review-preflight.py -R org/repo --pr 123

# Custom repo folder (default: ~/repos)
pr-review-preflight.py <PR_URL> --repo-folder ~/workspace
```

The script creates a review directory under `~/scratchpad/pr_reviews/{repo}-pr{number}/` containing:
- `pr-details.json` and `diff.txt`
- `{repo}/` -- an isolated git worktree (detached HEAD at the PR commit), using `~/repos/{repo}` as the shared object store
- `pr-comments/` -- scaffolded with `manifest.json` and `body.md` templates
- `post-review.sh` -- wrapper script for posting (see Phase 6)

If the PR body contains noisy rendered HTML, the script normalizes `github.body` for agent readability and writes the untouched original to `pr-body-raw.md`. It prints the **bare folder name** (e.g. `repo-pr60123`) to stdout. The full path is `~/scratchpad/pr_reviews/<bare-name>/`.

The JSON has three top-level keys: `github` (populated by the script), `categorization` (populated by the script, see below), and `context` (initially `null`, populated in Phase 2). All PR metadata, file lists, review comments, and thread resolution status are under `github`. `github.body` is the normalized review context; when a raw sidecar file exists, `github.bodyRawPath` points to it. `github.repoPath` points to the worktree directory for reading source files.

`categorization` is the output of the change-categorization step. The script parses changed paths from `diff.txt`, classifies each path into a bucket using the patterns in `pr-review-buckets.json` (next to the script), and computes which review lenses should run. The block has the form:

```json
"categorization": {
  "lensesToRun": ["security", "correctness", "quality", "testing"],
  "buckets": { "code": ["src/foo.ts"], "config": ["app.yml"] },
  "unknownExtensions": [".graphql"],
  "rationale": "buckets present (code, config) -> run: security, correctness, quality, testing"
}
```

`pr-review-buckets.json` is the source of truth for the bucket map and lens rules; do not duplicate the patterns here. Edit that file (and add tests) to extend or change the classifier.

**Existing directory**: if the review directory already exists (e.g. re-reviewing the same PR), the script exits with a non-zero status and an error message. Ask the user whether to delete the existing review. If approved, re-run with `--force` to delete and recreate.

Use `github.headRefOid` when posting line comments in Phase 6. Use `github.changelog` to extract linked Jira issue keys (the `issue_number` field) for Phase 2.

`github.authoredBySelf` is `true` when the PR author matches the current GHE user. Phases 2 through 4 still run normally; only the delivery channel changes at Phase 5. When set, present findings in chat for the user to act on as the PR author, and skip the GitHub post in Phase 6. See Phase 5 and Phase 6 below.

## Phase 2: Research

Gather additional context beyond what GitHub provides. After this phase, `pr-details.json` should contain everything a reviewer needs.

### Jira (if linked)

Look for a Jira issue key matching **PROJECT-NUMBER** (e.g. `PROJ-123`). Check in order: `github.changelog[].issue_number` -> `github.title` -> `github.body` -> `github.headRefName`.

If found:
1. Call `getAccessibleAtlassianResources` for cloud ID
2. Call `getJiraIssue` with the extracted key
3. If the MCP call fails, fall back to Glean (`read_document` with Jira URL or `search` with issue key)

### Glean

Use Glean `search` or `chat` to find related context that Jira alone does not capture: design docs, Confluence pages, Slack threads, or prior PRs. Query using the Jira key, PR title keywords, or relevant service/feature names from the diff.

### Update pr-details.json

Read `pr-details.json`, set the `context` field, and write the full object back:

```python
import json
from pathlib import Path

path = Path("<review-dir>/pr-details.json")
data = json.loads(path.read_text())
data["context"] = {
    "jira": {"key": "PROJ-123", "summary": "...", "acceptanceCriteria": "...", "status": "..."},
    "glean": "Design doc: <url>. Key constraint: ...",
    "notes": "any other observations",
}
path.write_text(json.dumps(data, indent=2) + "\n")
```

Omit `jira` if no issue was linked. Omit `glean` if no relevant results were found. Set `context` to `{}` (not `null`) even if both are empty, to signal that research was completed.

## Phase 3: Review

Read `categorization.lensesToRun` from `pr-details.json` and run only those lenses. If the field is missing (e.g. preflight predates the categorization feature), fall back to running all four lenses. An empty `lensesToRun` (e.g. docs-only PRs) means no lens analysis is needed; proceed directly to Phase 4 to read the diff for PR-level concerns (changelog, disclaimer, missing context).

### If running as a subagent (e.g. via `/fresh-eyes` or delegation)

Skip the subagent invocations and perform the analyses inline. For each lens in `categorization.lensesToRun`:

1. Read `<review-dir>/pr-details.json` for full context and `<review-dir>/diff.txt` for the diff. Use `github.repoPath` to read source files from the worktree.
2. Apply the security lens (auth, injection, PII, secrets, API risks, cryptography) - if listed
3. Apply the correctness lens (race conditions, null handling, transaction integrity, cross-file impact) - if listed
4. Apply the quality lens (duplication, OOP, performance, structural efficiency) - if listed
5. Apply the testing lens (missing coverage, mock abuse, fragile setup, assertion quality) - if listed
6. Collect all findings and proceed to Phase 4

### If running as the main agent

Spawn the subagents listed in `categorization.lensesToRun`, in parallel, in a single message. Below shows all four; emit only the calls whose lens names appear in the list:

```
Task(subagent_type="security-reviewer",   prompt="Read <review-dir>/pr-details.json for full PR context and <review-dir>/diff.txt for the diff. Use github.repoPath from pr-details.json to read source files. Apply your lens and return findings as a JSON array in a fenced ```json block.")
Task(subagent_type="correctness-reviewer", prompt="Read <review-dir>/pr-details.json for full PR context and <review-dir>/diff.txt for the diff. Use github.repoPath from pr-details.json to read source files. Apply your lens and return findings as a JSON array in a fenced ```json block.")
Task(subagent_type="quality-reviewer",     prompt="Read <review-dir>/pr-details.json for full PR context and <review-dir>/diff.txt for the diff. Use github.repoPath from pr-details.json to read source files. Apply your lens and return findings as a JSON array in a fenced ```json block.")
Task(subagent_type="testing-reviewer",     prompt="Read <review-dir>/pr-details.json for full PR context and <review-dir>/diff.txt for the diff. Use github.repoPath from pr-details.json to read source files. Apply your lens and return findings as a JSON array in a fenced ```json block.")
```

Each subagent reads the context file, diff file, and local repo files, then returns findings as a JSON array. An empty array `[]` means no issues found for that lens. If a subagent returns malformed output, attempt to extract findings with tolerant parsing before treating it as a failure.

#### Subagent failure handling

If a subagent returns an error status:

1. **Retry once**, including any error context in the retry prompt.
2. **If retry also fails**, perform that lens's analysis directly inline: read the agent file (`agents/<lens>-reviewer.md`) for the lens, then run the analysis yourself.
3. **Surface the fallback** in the user-facing summary.

## Phase 4: Consolidate, verify, and confirm

Read the actual files and diff (from `<review-dir>/diff.txt`, or `git -C <review-dir>/{repo} diff origin/<baseRefName>...HEAD` for file-scoped checks) to process the findings from Phase 3:

1. **Consolidate first**: where two findings describe the same underlying problem across lenses, keep the most informative one. Prefer: blocking over non-blocking, more specific path+line, longer description. Use your understanding of the actual code, not string-matching. Do this before verification so a single bug is not verified more than once.
2. **Verify code-bug findings (subagent per finding)**: for each consolidated finding that asserts a *reproducible code defect* -- a specific `path:line` where the code behaves incorrectly (correctness bugs, security vulnerabilities, data-integrity risks, breaking changes) -- spawn a `finding-verifier` subagent to confirm it. These are the findings that typically carry `blocking: true` or `label: issue`, but apply the `path:line`-defect test, not the labels: a `blocking` non-code finding (e.g. a missing changelog block) is not verified here. Each verifier reproduces the defect in its own isolated worktree, authors and runs a minimal failing test for code bugs, and returns a verdict. Then:
   - Drop findings the verifier returns as `false-positive`, and record them (with the verifier's reason) for display in Phase 5; do not post them.
   - For findings confirmed `real`, attach the repro test (`testCode`, `testPath`) and `testOutput` so they can be cited as evidence in the comment (Phase 5).
   - Keep `uncertain` findings, but mark them "unverified" so the draft can flag that execution did not confirm them.
3. **Confirm soft findings inline**: for the remaining findings that are not reproducible code defects (quality, naming, missing-test coverage, style, PR-level concerns), confirm each is real by reading the code yourself. Discard clear false positives and note why. These do not get a verifier subagent.
4. **Suppress non-additive findings**: cross-reference against existing review comments. If a finding is genuinely already covered by a prior comment that is still open (unresolved), exclude it from what gets posted but still show it to the user as "already flagged by prior review." Ignore resolved threads entirely; do not reference, rebut, or call out resolved comments in your review.
5. **Identify fixed threads**: check unresolved threads from `pr-details.json` (`github.reviewThreads` where `isResolved` is false). If the current changes address an unresolved thread, collect its `id` for resolution in Phase 6.
6. **Sort**: blocking findings first, then by file and line.
7. **Check preflight warnings**: if `github.preflightWarnings` is non-empty, include each warning as a finding (label: `chore`, non-blocking, no path/line). These go in the review body, not as line-level comments.

Produce a clean, validated list for Phase 5.

### Spawning verifiers

Assign each finding a stable `findingId` that is safe to use in a filesystem path: a short alphanumeric/kebab slug such as `correctness-1` or `security-2` (no spaces, slashes, or colons -- the verifier builds a worktree path from it).

**If running as the main agent**, spawn one `finding-verifier` per reproducible code-bug finding, in parallel, in a single message. Hand each one the finding as a JSON object, the review worktree path (`github.repoPath`), and the path to `pr-details.json`:

```
Task(subagent_type="finding-verifier", prompt='Verify this finding. Repo path: <review-dir>/{repo}. Context: <review-dir>/pr-details.json. Finding: {"findingId": "correctness-1", "path": "src/x.ts", "line": 42, "title": "...", "description": "...", "blocking": true, "label": "issue"}. Reproduce it in your own isolated worktree per your instructions and return your verdict JSON.')
```

Each verifier returns a single JSON object (`findingId`, `verdict`, `reasoning`, `testPath`, `testCode`, `testOutput`). If a verifier errors, retry once; if it fails again, fall back to confirming that finding inline (read+trace, no execution) and mark it "unverified" in the draft.

**If running as a subagent yourself** (e.g. via `/fresh-eyes` or delegation), you cannot spawn nested subagents: read `agents/finding-verifier.md` and perform its Method inline for each reproducible code-bug finding (isolated worktree, minimal failing test, teardown). This runs sequentially, so it is slower than the parallel main-agent path; for a PR with many code-bug findings it may take a while.

### Recommendation

Apply the three-outcome recommendation logic from the Principles section above (hard block, soft block, recommend approval) to the validated findings.

## Phase 5: Draft review and get approval

### Self-review short-circuit

If `github.authoredBySelf` is `true`, do not draft a review comment for posting. Instead, present the validated findings directly in chat for the user to act on as the PR author. Do not prompt to post; skip Phase 6 entirely. The user will follow up with fixes or further questions in chat.

### Normal path

Present findings and the draft review comment in a single response. Follow the Comment format and approval section above for tone and content. For findings confirmed `real` by a verifier, cite the repro as evidence in the line comment (the failing test and a trimmed line or two of `testOutput`); this is the strongest form of feedback for the author. Note any findings that were verified false positives (and excluded) and any kept as "unverified" (verifier could not execute). If any lenses fell back to inline analysis (subagent failure), note that in your recommendation. State which lenses ran and which were skipped (read from `categorization.lensesToRun`) so the user can challenge the categorization decision before approving the post. If `categorization.unknownExtensions` is non-empty, surface those extensions and offer to update `pr-review-buckets.json` after the review is posted.

```
**Draft Review Comment (will be posted to PR author):**

[Full text of the review comment - feedback for the author only]

---

**Lenses applied:** <comma-separated list>  (skipped: <list, with brief reason>)
**Unknown extensions:** <list, only if non-empty - offer to update pr-review-buckets.json>

**My Recommendation (for you):** <hard block / soft block / recommend approval> - <brief explanation>

Post this review? (yes/no)
```

## Phase 6: Post review

Skip this phase entirely when `github.authoredBySelf` is `true`. The findings were presented in chat in Phase 5 for the user to act on as the author; do not post to GitHub.

When the user approves the draft, post the review body and all line-level comments as a single atomic review using `post-pr-review.py`.

### Review directory structure

The preflight script creates the full review directory with scaffolded templates:

```
<review-dir>/
    pr-details.json          (from preflight)
    diff.txt                 (from preflight)
    {repo}/                  (git worktree, detached HEAD at PR commit)
    post-review.sh           (wrapper script for posting)
    pr-comments/
        manifest.json        (scaffolded, fill in findings)
        body.md              (scaffolded with disclaimer, write review above it)
        comment-1.md
        comment-2.md
```

### Write review files

Findings specific to a single line or small block of lines must be line-level comments. The review body is for PR-level observations and brief references to inline findings (label, subject, file); the line comment carries the detail. Do not put line-specific feedback in the body.

1. **Review body** (`body.md`): The scaffolded file already contains the disclaimer. Write your PR-level summary per the Comment format and approval section above the disclaimer block.

2. **Line-level comments** (`comment-1.md`, etc.): One file per inline finding, formatted per the Comment format and approval section. End each with disclaimer from the `pr-disclaimers` rule.

3. **Manifest** (`manifest.json`):

```json
{
  "event": "COMMENT",
  "body_file": "body.md",
  "comments": [
    {
      "path": "src/file.ts",
      "line": 42,
      "body_file": "comment-1.md"
    }
  ],
  "resolve_thread_ids": ["PRRT_kwDO..."]
}
```

Set `event` per the Principles section recommendation outcome (`COMMENT` or `REQUEST_CHANGES`). Optional comment fields: `start_line` (for multi-line comments), `side` and `start_side` (default `RIGHT`). Both `line` and `start_line` must be added/modified lines in the diff; context lines and files not in the diff cannot take inline comments and must go in the body instead. Optional `resolve_thread_ids`: list of GraphQL thread node IDs (from `pr-details.json`) to resolve after posting. Include threads identified as fixed in Phase 4 step 4.

### Post

Run the wrapper script in the review directory. It resolves the review folder and calls `post-pr-review.py` with the bare folder name:

```bash
<review-dir>/post-review.sh
```

If validation fails, the script prints all errors and exits without making any API call. Fix the errors and rerun.

### Cleanup

After posting, delete the review directory (`rm -rf <review-dir>`). The `sync-repos` script prunes stale worktree references automatically on its next run. No manual worktree cleanup is needed.

If the diff is stale (e.g. new commits were pushed), regenerate it from the worktree before re-running the review:

```bash
git -C <review-dir>/{repo} fetch origin
git -C <review-dir>/{repo} diff origin/<baseRefName>...HEAD > <review-dir>/diff.txt
```
