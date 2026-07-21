---
slug: pause-session
name: pause-session
description: Use when stopping a plan/implementation session before it's finished and picking it back up later — captures progress, decisions, and the next concrete step to a small handoff file, and reloads only that file (not full history) at the start of the next session to resume cheaply.
usage: |
  /pause-session          # save current progress to a handoff file
  /pause-session resume   # load the handoff file for this branch and resume
---

# Pause Session

Save just enough state to resume work later without re-reading the full conversation, plan, or diff.

## When to Use

- Stopping mid-task/mid-plan and picking it up in a future session (today, tomorrow, next week)
- Starting a session that should continue previously paused work
- **Not** for finished work — use `superpowers:finishing-a-development-branch` instead
- **Not** a substitute for a plan document — if using `superpowers:writing-plans`, this skill just points back at it plus the delta since the plan was written

## Handoff File

One file per branch, overwritten on each pause: `.claude/sessions/<branch>.md`
(replace `/` in branch names with `-`, e.g. `feature/x` → `feature-x.md`)

`.claude/sessions/` is gitignored — it's local working memory, not a deliverable.

Target **under 300 words**. This is the only thing the next session should need to read to resume — so every line must earn its place.

```markdown
# <branch> — paused <date>

## Status
One sentence: what's done, where you stopped.

## Next step
The single concrete action to take first. Not "continue working" — the actual command,
file, or decision.

## Decisions made
Only non-obvious rationale (why X over Y). Skip anything derivable from the code/diff.

## Open questions / blockers
Anything unresolved that the next session needs to address or ask the user about.

## Files touched
Path list, not a diff — `git diff --stat` covers the rest.

## Verify
Command(s) to confirm the saved state still holds (e.g. `pytest tests/foo`).

## Plan reference
Path to the plan doc + current task/step number, if one exists.
```

## Pausing: Steps

1. `git branch --show-current` to name the file.
2. Fill in the template above from what actually happened this session — not a transcript, a summary.
3. Write to `.claude/sessions/<branch>.md`, overwriting any prior handoff for this branch.
4. Tell the user where it's saved. Don't commit or push it without asking, same as any other change.

## Resuming: Steps

1. `git branch --show-current`, look for `.claude/sessions/<branch>.md`.
   - Not found: say so, ask what to resume — don't fabricate context.
2. Read **only that file**. Don't re-read the full plan doc, git log, or old messages unless the handoff explicitly points there for one specific detail.
3. Run `git status --short` and `git diff --stat` — confirm files-touched still matches the handoff. If it doesn't (someone else pushed, branch moved), flag the mismatch before proceeding.
4. Summarize the handoff back to the user in 2-3 sentences plus the next step, and confirm before continuing — the user may want to redirect.
5. Once the branch is merged or the work is abandoned, delete the handoff file.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Writing a play-by-play narrative | Summarize state, don't retell the session |
| Vague next step ("continue working on X") | Name the exact file/command/decision to start with |
| Resuming without checking `git status` first | Repo state may have moved since the handoff was written — verify, don't assume |
| Handoff file lingers after the branch is merged | Delete it as part of finishing the branch |
| Re-reading the whole plan/conversation on resume | Defeats the purpose — the handoff file *is* the summary |

## Integration

- **superpowers:writing-plans** / **superpowers:executing-plans** — if a plan doc exists, reference it by path + step number rather than duplicating its content here
- **superpowers:finishing-a-development-branch** — use that instead once work is actually complete, not paused
