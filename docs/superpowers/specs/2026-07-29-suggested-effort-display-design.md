# Suggested Effort Display

**Date:** 2026-07-29
**Status:** Approved

## Problem

Program templates prescribe an effort target per scheme (`target_rpe`, `intensity_pct`), and the
backend already converts it into a per-slot `effort_target`. But two gaps keep that target from
reaching the user:

1. **A skipped effort method suppresses every target.** The program wizard's first option is
   "Not sure yet / skip", which writes `effort_method: null` into `program.constraints`.
   `preview._effort_target` returns `None` whenever the method is null, so no suggested effort
   renders anywhere — even though the template has a `target_rpe` on every scheme.
2. **Loaded exercises show no effort at all.** `formatEffortDisplay` prefers weight over effort,
   so a main lift reads `4 x 5 @80 kg` and nothing more. Meanwhile `SetRow` still *requires* an
   effort entry when logging, with no target on screen to anchor it against.

Accessories are unaffected by gap 2: loads come only from the template's `required_inputs`
(`squat_start`, `bench_start`), so accessory slots have `base_load: None` and already render
`3 x 12 @ RPE 7`.

## Two axes, deliberately separate

Effort appears on two independent axes, and this design does not merge them:

- **Prescription** — what the program tells the user to aim for. Derived from the template's
  `target_rpe` / `intensity_pct`, expressed in the *program's* effort method
  (`program.constraints.effort_method`). This is what the design changes.
- **Reporting** — how the user says the set actually felt. Stored per set on
  `WorkoutSetLog.effort_method`, driven by the user's profile preference, and normalised back to
  the canonical 0-10 RPE scale by `autoregulation._to_rpe_scale`. **Unchanged by this design.**

A program that prescribes in `%1RM` while the user reports in RPE is correct, not a bug.

## Scope

Templates need no changes. All 10 seeded templates already carry `target_rpe` and `intensity_pct`
on every scheme (main 8.0/0.80, accessory 7.0/0.65).

### 1. Backend — a skipped effort method means RPE

In `backend/app/services/program/preview.py`, `_effort_target` currently bails on a null method.
Invert the guard so only a missing `target_rpe` suppresses the target:

```python
if target_rpe is None:
    return None
method = effort_method or "rpe"
```

The remaining branches (`rpe`, `rir`, `borg`, `percent_1rm`) are unchanged, including
`percent_1rm`'s existing requirement that `intensity_pct` be present.

Effort targets resolve at week-derivation time rather than draft time, so existing draft and
active programs pick this up immediately. No migration, and `program.constraints` is not
rewritten.

`drafting._base_load_for` also reads `effort_method`, but only to test for `percent_1rm`. A null
method already falls through to its raw-value branch, so base loads are unaffected.

### 2. Frontend — effort as a separate qualifier

`formatEffortDisplay` keeps its current contract: weight wins, effort fills in only when there is
no load. Every existing call site keeps its current output.

A new sibling lands in `frontend/src/utils/effortDisplay.ts`:

```ts
formatEffortSuffix(load: number | null, effortTarget: EffortTarget | null): string | null
```

It returns `RPE 8`, `RIR 2`, `Borg 18`, or `80% 1RM`, and returns `null` when there is no target
**or** when `load === null` — in that case the effort already sits inside the main string, and a
suffix would duplicate it. Both functions share a single method-to-label mapping so the
precedence rule lives in one file instead of being re-derived by each component.

The suffix renders in the three surfaces that have a detail tier:

| Surface | Placement |
|---|---|
| `ExerciseSection` (tracking) | appended to the expanded `Target: …` line; the collapsed header keeps the plain `formatEffortDisplay` string |
| `SlotRow` (plan preview) | an extra chip in the existing flex-wrap row, beside `Rest` / note / rotation |
| `ExerciseSlotCard` (plan preview) | the same chip row |

`SetRow`'s summary and `SessionDetailPage` are untouched. Both are dense one-line recaps of what
was *performed*, not prescriptions.

Resulting tracking view:

```
▾ Bench Press      4 x 5 @80 kg    0/4 sets
   Target: 4 x 5 @80 kg · RPE 8 · Rest 2:00

▾ Cable Fly        3 x 12 @ RPE 7  0/3 sets
   Target: 3 x 12 @ RPE 7 · Rest 1:00
```

One deliberate wording change: `formatEffortDisplay`'s no-load `percent_1rm` branch currently
renders `@80%`. It becomes `@80% 1RM` to match the suffix. This updates one existing test.

## Decisions taken

- **No effort ranges.** `target_rpe` stays a single value per scheme; targets render as `RPE 7`,
  not `RPE 6.5-7.5`. Ranges can be revisited later by adding `target_rpe_min`/`target_rpe_max` to
  the scheme definition.
- **No per-set hint while logging.** The effort input keeps its `0` placeholder and stays empty.
  The exercise block's `Target:` line is the single place the user reads the prescription, which
  also avoids nudging users toward rubber-stamping the target — that would poison the
  autoregulation signal.
- **Weight keeps precedence in the compact string.** Headers and one-line recaps stay
  `4 x 5 @80 kg`. Effort rides alongside as a separate element rather than lengthening that
  string.
- **The wizard keeps its "Not sure yet / skip" option.** Skipping now means RPE rather than
  meaning no prescription.

## Testing

TDD per `CLAUDE.md` — tests first, then implementation.

**Backend** (`test_effort_method.py`, `test_preview.py`): a null program effort method yields an
`rpe` target rather than `None`; a null `target_rpe` still yields `None`; the four explicit
methods are unchanged.

**Frontend**: new unit tests for `formatEffortSuffix` covering each method, the no-target case,
and suppression when `load === null`. Assertions added to `ExerciseSection.test.tsx` (suffix on
the `Target:` line, absent from the header), `SlotRow` and `ExerciseSlotCard` tests (suffix chip
present for loaded slots, absent for loadless ones), and `WorkoutTrackingPage.test.tsx`. The
existing `@80%` expectation in `effortDisplay.test.ts` updates to `@80% 1RM`.
