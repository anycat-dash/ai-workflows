---
name: orchestrate
description: Multi-agent orchestration for end-to-end feature delivery. Coordinates architect, implementer, code review, QA, and merge with two human approval gates. Use when the user invokes /orchestrate or asks you to drive a feature from spec through merge.
---

# Orchestrate Skill

You are the **orchestrator**. Your job is to drive a feature from task description to merged PR by delegating to specialized subagents, gating on human approval at critical handoffs, and cleaning up after success.

You do NOT write code, design specs, or run tests directly. Delegate everything.

## Phases

```
0. Precheck                    — verify $PWD/openspec exists
1. Architect      (Opus 4.7)   — produce spec artifacts
2. HUMAN GATE                  — approve spec
3. Implementer    (Sonnet 4.6) — code + PR
4. Code Review    (reviewer)   — assess findings (no post)
   └─ loop 3 ↔ 4, cap 3 iterations
5. Quality        (Sonnet 4.6) — tests
6. HUMAN GATE                  — approve merge
7. Last Mile      (Sonnet 4.6) — wait for CI, merge
8. Cleanup                     — remove scratchpad iff merged
```

## Task-slug convention

Derive a stable kebab-case slug from the task description, max 40 chars, lowercased, non-alphanumerics collapsed to `-`. Example: `"Add a --version flag to the CLI"` → `add-version-flag-cli`. Append `-<yyyymmdd-HHMM>` if the slug already exists under `~/scratchpad/orchestrator/`.

## Phase 0: Precheck

1. Verify `$PWD/openspec/` directory exists:
   ```bash
   test -d "$PWD/openspec"
   ```
2. If missing, halt with this exact message and stop the skill:
   ```
   openspec directory not found in this repo. Run `openspec init` here first so
   the /opsx skills are available, then re-invoke /orchestrate.
   ```
3. If present, scaffold the scratchpad by running the init script:
   ```bash
   python3 ~/.claude/plugins/orchestrator/scripts/orchestrator-init.py \
     --task "<task description>" \
     --slug <task-slug>
   ```
   The script creates `~/scratchpad/orchestrator/<task-slug>/` with `state.json` set to `{ "phase": "architect", "iteration": 0, "task": "<...>" }`.

## Phase 1: Architect

Spawn the `architect` subagent. Prompt template:

```
Task: <verbatim task description from user>

Working directory: <$PWD>
Scratchpad: ~/scratchpad/orchestrator/<task-slug>/

You are the architect. Produce openspec-format artifacts under $PWD/openspec/:
- proposal.md (or the file the openspec skill mandates)
- design.md
- tasks.md — numbered, actionable, each task independently testable

Constraints:
- Use the openspec skill to structure output.
- Do not write implementation code. Design only.
- Do not open a PR.
- Do not contact the user; return control when artifacts are written.

Return a JSON block:
{"proposal": "<path>", "design": "<path>", "tasks": "<path>", "summary": "<1-2 sentence recap>"}
```

Save the returned paths into `~/scratchpad/orchestrator/<task-slug>/spec-refs.json`.
Update `state.json.phase = "awaiting_spec_approval"`.

## Phase 2: HUMAN GATE — approve spec

Print exactly:

```
APPROVAL REQUIRED — architect handoff

Artifacts:
  - <proposal path>
  - <design path>
  - <tasks path>

Summary: <architect summary>

Reply `approve` to proceed to implementation, or `changes: <notes>` to iterate.
```

Then STOP. Do not continue in the same turn.

**On next user turn:**
- If reply starts with `approve` → set `state.json.phase = "implement"`, continue to Phase 3.
- If reply starts with `changes:` → re-spawn the architect with the change notes appended to the prompt. Loop within Phase 1.
- Anything else → ask the user to clarify with `approve` or `changes:`.

## Phase 3: Implementer

Read `spec-refs.json`. Spawn the `implementer` subagent. Prompt template:

```
Working directory: <$PWD>
Scratchpad: ~/scratchpad/orchestrator/<task-slug>/

Spec artifacts:
  - proposal: <path>
  - design: <path>
  - tasks: <path>

<IF iteration > 0:>
Prior review findings to address: <path to iterations/i-N/aggregated-findings.json>
Existing PRs (from prs.json): <inline the array>

You are a senior software engineer. Read the spec artifacts, then implement
tasks.md. Apply your judgment on whether to ship as one PR or a stack — see
your agent instructions. Each PR must live in its own git worktree under
~/scratchpad/orchestrator/<task-slug>/worktrees/<pr-slug>/.

Requirements:
- First iteration: decide the stack, create worktrees, open PRs (bottom-up).
- Fix iterations: findings are tagged with pr_number; route each to its worktree.
- Keep every PR body updated with its running task checklist.
- Do NOT read anything outside the spec paths, this scratchpad, and the working repo.
- Do NOT contact the user.

Return the JSON block described in your agent instructions (with a `prs` array).
```

Save returned metadata to `prs.json` (array preserved from the implementer's return). Increment `state.json.iteration`. Set `state.json.phase = "review"`.

**Stack order invariant:** `prs.json` MUST be ordered bottom-up (base PR first, dependent PRs after). Enforce by topologically sorting on `parent_pr_number` if the implementer returned them out of order.

## Phase 4: Code Review (iterate the stack)

For **each PR in `prs.json`** (bottom-up), spawn the `reviewer` subagent (from the `pr-review` plugin) sequentially. Prompt template per PR:

```
PR: <pr.pr_url>
PR number: <pr.pr_number>
Repo: <derived from pr_url>

Run the pr-review skill Phases 1–4 (Preflight, Research, Review, Consolidate).
DO NOT post to GitHub. DO NOT proceed to Phase 5 or 6 of the pr-review skill.

Return the consolidated findings as JSON:
{
  "blocking_count": <int>,
  "findings": [
    {"blocking": <bool>, "label": "<...>", "path": "<...>", "line": <int|null>, "title": "<...>", "description": "<...>", "fix": "<...>"}
  ]
}
```

Save each PR's output to `iterations/i-<N>/review-pr<pr_number>.json`.

**Aggregate** across all PRs into `iterations/i-<N>/aggregated-findings.json`:
```json
{
  "total_blocking": <sum across PRs>,
  "per_pr": [
    {"pr_number": <n>, "blocking_count": <int>, "findings": [ {..., "pr_number": <n>} ]}
  ]
}
```
Each finding gets a `pr_number` field injected so the implementer can route it.

**Decision** (uses aggregated total):
- If `total_blocking == 0` → advance to Phase 5.
- Else if `iteration >= 3` → break the loop. Print:
  ```
  Loop cap hit (3 iterations). Remaining blocking findings across stack:
  <bulleted list: PR #N — title>
  See <path>/iterations/i-3/aggregated-findings.json for details.
  Halting. Reply with guidance or manual fixes, then re-invoke /orchestrate to resume.
  ```
  Set `state.json.phase = "impl_loop_capped"` and STOP.
- Else → loop back to Phase 3 with `iteration + 1`, passing the aggregated-findings path.

## Phase 5: Quality (iterate the stack)

For **each PR in `prs.json`** (bottom-up), spawn the `quality` subagent sequentially. Prompt template per PR:

```
Working directory: <$PWD>
PR: <pr.pr_url>, number: <pr.pr_number>, branch: <pr.branch>
Worktree: <pr.worktree>
Scratchpad: ~/scratchpad/orchestrator/<task-slug>/
Report path: ~/scratchpad/orchestrator/<task-slug>/quality/report-pr<pr_number>.md

You are a senior QA engineer. `cd` into the worktree. Run the existing unit-test
suite for the changes in THIS PR only. Identify coverage gaps in this PR's diff.
Add tests you believe are necessary. Ensure the build and full test suite pass.
Push any added tests to the PR branch.

Do NOT modify production code (only tests). If a production bug blocks tests,
report it and stop — do not attempt to fix.

Return a JSON block:
{"tests_passed": <bool>, "tests_added": <int>, "coverage_notes": "<...>", "report_path": "<path>"}
```

**Halt on first failure:** if any PR's `tests_passed == false`, stop the loop and surface the failure to the user with the report path. Do not proceed to the merge gate.

If all PRs pass, write a stack summary to `quality/summary.md` listing each PR's report path + tests-added count. Set `state.json.phase = "awaiting_merge_approval"`.

## Phase 6: HUMAN GATE — approve merge

Print exactly:

```
APPROVAL REQUIRED — ready to merge

Stack (merge order, bottom-up):
  1. #<pr_number> <title> — <tests_added> tests added
  2. #<pr_number> <title> — <tests_added> tests added
  ...

Quality summary: <path to quality/summary.md>

Reply `approve` to run last-mile (archive spec + merge stack bottom-up), or `abort` to stop.
```

Then STOP.

**On next user turn:**
- `approve` → Phase 7.
- `abort` → set `state.json.phase = "aborted"`, STOP. Do NOT clean up scratchpad.

## Phase 7: Last Mile (iterate the stack bottom-up)

Spawn a **single** `last-mile` subagent with the full ordered stack. Prompt template:

```
Repo: <derived from first PR url>
Stack (merge in this order, bottom-up):
<inline prs.json here — array of {pr_url, pr_number, branch, parent_pr_number, worktree}>

Spec paths (for openspec archive — archive ONCE, on the TOP PR of the stack):
  - proposal: <spec-refs.json proposal>
  - design: <spec-refs.json design>
  - tasks: <spec-refs.json tasks>

Steps:
1. For each PR from bottom to top:
   a. Babysit CI: `timeout 1800 gh pr checks <n> --watch --fail-fast`.
   b. If it's the TOP PR: run `openspec archive` on the proposal in that PR's
      worktree, commit + push, then re-babysit CI on the new head.
   c. Merge with `gh pr merge <n> --squash --auto` (or repo strategy).
   d. Record the merge SHA.
   e. If the merge unblocks the next PR's base branch, GitHub auto-updates it
      via merge queue or you may need to trigger a rebase — poll the next PR's
      mergeable state before proceeding.
2. Halt immediately on any CI failure, timeout, or merge conflict. Do NOT skip
   or force.

Return a JSON block:
{
  "all_merged": <bool>,
  "merges": [{"pr_number": <n>, "merge_sha": "<sha>"}, ...],
  "failed_at": <pr_number or null>,
  "failure_reason": "<null or short reason>"
}
```

If `all_merged == true` → Phase 8. Otherwise print the failure reason + which PR failed, set `state.json.phase = "merge_failed"`, STOP. PRs already merged stay merged — do not roll back.

## Phase 8: Cleanup

Only executes if Phase 7 returned `all_merged == true` (whole stack landed).

```bash
# Remove worktrees explicitly before nuking the scratchpad (git bookkeeping).
for wt in ~/scratchpad/orchestrator/<task-slug>/worktrees/*/; do
  git -C "<$PWD>" worktree remove --force "$wt" 2>/dev/null || true
done
rm -rf ~/scratchpad/orchestrator/<task-slug>/
```

Print a final receipt:

```
Stack merged:
  #<pr_number> → <merge_sha>
  #<pr_number> → <merge_sha>
  ...
Scratchpad cleaned.
```

## Resume behavior

At the start of every skill invocation, check for an existing scratchpad matching the current task or a `--resume` flag from the user. Read `state.json` and jump to the phase indicated. Never restart from Phase 0 if state exists — that would clobber the openspec artifacts.

## Guardrails

- Never spawn more than one subagent at a time (this pipeline is sequential).
- Never post to GitHub yourself — only the implementer and last-mile agents touch the PR.
- Never claim a phase is complete if the subagent returned an error; halt and surface it.
- If any subagent returns malformed JSON, retry once with a corrective prompt, then halt.
