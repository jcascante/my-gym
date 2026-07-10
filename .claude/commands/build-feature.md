# build-feature

Implement and validate a small feature using a two-tier model workflow: Haiku for cheap, scoped implementation; Sonnet for quality review.

## Usage

```
/build-feature <task description>
```

Example:
```
/build-feature add a logout endpoint that clears the refresh token cookie
```

## Workflow

1. **Implementation**: Spawn the `feature-builder` agent (Haiku) with your task description. It implements the feature following MyGym conventions, runs tests/lint/type-check, and reports back.

2. **Validation**: Once the builder finishes, spawn the `quality-reviewer` agent (Sonnet) with the same task description plus the resulting diff. It validates tests, lint, types, and checks the code for correctness and quality issues.

3. **Findings**: If the reviewer finds issues, you'll be asked whether to:
   - **Send back to builder**: the builder re-runs with the specific findings as a new task (e.g., "fix the following issues: [list]").
   - **Handle manually**: you fix the issues yourself or ignore them.

   If no issues are found, the workflow stops (you can now commit and push).

4. **Costs**:
   - Feature builder: ~1 Haiku run (~10–50 min-tokens depending on task size).
   - Quality reviewer: ~1 Sonnet run (~20–100 min-tokens depending on code size).
   - Re-fix cycle (if needed): 1 more Haiku run.
   - Total: ~$0.01–$0.05 per small feature (vs. ~$0.50–$2.00 if you used Opus or Sonnet for the whole task).

## When to Use

- Small, well-scoped tasks: bug fixes, new endpoints, refactors, feature flags.
- When you want quality validation without paying Opus/Sonnet rates for implementation.

Not ideal for:
- Large, complex features spanning multiple domains (use `/plan` + your own agent choice instead).
- Tasks requiring multiple rounds of back-and-forth with requirements clarification.
