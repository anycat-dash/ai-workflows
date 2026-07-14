---
name: orchestrate
description: End-to-end feature delivery via multi-agent chain — architect, implement, review, QA, merge. Two human approval gates.
---

When the user invokes `/orchestrate <task-description>` (or asks you to run this command):

1. **Capture the task description.** Everything after `/orchestrate` is the feature request. If empty, ask the user for one sentence describing what they want built, then continue.

2. **Follow the `orchestrate` skill.** Load `skills/orchestrate/SKILL.md` and execute its phases in order. The skill handles precheck, subagent spawning, approval gates, the implementation ↔ review loop, and cleanup.

3. **Do not shortcut.** Do not skip the openspec precheck, do not skip approval gates, do not exceed the 3-iteration loop cap. The skill enforces these — follow it.

4. **Resume behavior.** If the user replies after an approval gate (`approve` / `changes: …`), read `state.json` under `~/scratchpad/orchestrator/<task-slug>/` to determine the next phase and continue.
