---
slug: build-feature
name: build-feature
description: Implement and validate a feature using Haiku (cheap) + Sonnet (quality review)
usage: |
  /build-feature <task description>

  Example:
    /build-feature add validation for workout log entries
---

# Build Feature: Two-Tier Workflow

Implement small features cheaply with Haiku, then validate with Sonnet — saving ~90% on token costs while keeping quality high.

## How It Works

1. **You describe the task** — e.g., "add a logout endpoint that clears the refresh token".
2. **Haiku implements it** (via `feature-builder` agent) following MyGym conventions, runs tests/lint/types.
3. **Sonnet reviews it** (via `quality-reviewer` agent) — runs full validation, reports any bugs/quality issues.
4. **You fix or accept** — if issues found, optionally send them back to Haiku for re-work.

## Cost Comparison

| Approach | Cost | Token Count |
|----------|------|-------------|
| Haiku only (no review) | ~$0.001–0.003 | 300–1000 in-tokens, Haiku output |
| Haiku + Sonnet review | ~$0.01–0.05 | 500–1500 in-tokens, Haiku + Sonnet output |
| Sonnet entire task | ~$0.05–0.20 | 1000–3000 Sonnet in-tokens |
| Opus entire task | ~$0.15–0.60 | 2000–5000 Opus in-tokens |

**Result**: `/build-feature` costs 75–90% less than using Sonnet/Opus for implementation.

## When to Use

**Good fits**:
- Bug fixes ("fix the logout flow to remove refresh token")
- Small new endpoints ("add a GET /workouts endpoint")
- Component updates ("add form validation to the login page")
- Simple refactors ("rename UserWorkoutLog.created_at to timestamp")

**Not ideal**:
- Large features spanning multiple domains
- Unclear requirements (use `/plan` first to clarify)
- Complex business logic requiring multiple review rounds

## Workflow Detail

### Step 1: Implementation (Haiku)

You invoke: `/build-feature add a GET endpoint to fetch user's current program`

The `feature-builder` agent (Haiku):
- Reads CLAUDE.md and relevant skill docs
- Implements the feature following patterns in the codebase
- Writes tests first (TDD)
- Runs `pytest`, `mypy`, `ruff check`, ESLint, type-check
- Reports back: what changed, files touched, any errors
- Does NOT commit or push

### Step 2: Review (Sonnet)

Once the builder finishes, the `quality-reviewer` agent (Sonnet):
- Reads the implementation + git diff
- Runs full test suite, linting, type checking
- Reviews for correctness: does it do what was asked?
- Checks for bugs: null checks, error handling, edge cases
- Validates patterns: async/await, auth checks, logging, etc.
- Reports findings (if any) via structured `ReportFindings` tool
- Does NOT edit code

### Step 3: Fix or Accept

If the reviewer found issues:
- **Option A**: "Send back to builder" → Haiku re-runs with the specific findings as a new task
- **Option B**: "Handle manually" → you review and fix the issues yourself
- **Option C**: "No issues" → you can commit and merge

If no issues found, you're done — commit and merge.

## Implementation Details

- **Haiku agent**: `.claude/agents/feature-builder.md` (model: haiku, full tool access)
- **Sonnet agent**: `.claude/agents/quality-reviewer.md` (model: sonnet, read-only tools)
- **Command**: `.claude/commands/build-feature.md` (orchestration guide)

Both agents follow MyGym's CLAUDE.md conventions and invoke skills as needed.

## Tips

- **Be specific**: "add validation to the workout form" is better than "improve the form".
- **Keep it scoped**: one feature per `/build-feature` invocation.
- **Check output**: review the builder's report and the reviewer's findings — don't assume everything is perfect.
- **Use refactor patterns**: if you need to rename things or restructure, use the `simplify` skill after implementation.

## Cost Estimate for This Project

- Average small feature: 1 Haiku run + 1 Sonnet run = ~800 Haiku in-tokens + ~1500 Sonnet in-tokens = **~$0.015–$0.03 per feature**.
- If using Opus alone: ~3000 Opus in-tokens = **~$0.15–$0.30 per feature** (10–20x more expensive).
- Over 20 features: `/build-feature` = ~$0.30–$0.60 total, Opus = ~$3–$6 total. **Savings: ~$2.40–$5.40 (90% reduction).**
