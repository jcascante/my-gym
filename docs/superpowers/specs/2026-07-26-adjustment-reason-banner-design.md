# Design: Load-Adjustment Reason Banner

**Date:** 2026-07-26
**Status:** Approved, ready for planning

## Problem

`PROGRAM_ENGINE_REFACTOR_PLAN.md` (Phase 4 sensor-layer UI, line 184) calls for:

> banner when the controller adjusted today's loads or a reactive deload fired, with a one-line reason ("recent sessions ran harder than planned — load reduced 5%")

Phase 4's backend logic (autoregulation, reactive deload) is fully implemented and merged, but nothing surfaces *why* a load changed to the user. Both `autoregulation.compute_adjustment` and `deload.compute_deload_trigger` already compute a `reason` string — `backend/app/services/program/preview.py` discards both (`_reason` at line 144, `_reactive_deload_reason` at line 120, underscore-prefixed and unused). The only artifact that reaches the frontend is a bare tag on the per-slot `note` field (`"autoregulated"` / `"reactive_deload"`), which `WorkoutTrackingPage.tsx` (lines 299–306) prints verbatim, unformatted, for the currently-viewed exercise only.

## Scope

Two distinct signals, two distinct UI treatments (confirmed with user):

1. **Reactive deload** (readiness-driven, workout-wide) → a single dismissible banner at the top of `WorkoutTrackingPage`.
2. **Autoregulation** (RPE-driven, per-exercise) → a friendlier version of the existing per-exercise "Note" section.

No new endpoint: both signals already flow through `GET /programs/{id}/preview` (`derive_week`), which is the same endpoint both the multi-week `DraftProgramView` review page and `WorkoutTrackingPage` (via `useWorkoutDetails` → `useProgramPreview`) already consume.

## Backend Changes

### `backend/app/services/progression/autoregulation.py`
Add a pure function alongside `compute_adjustment`:

```python
def describe_adjustment(factor: float) -> str | None:
    """One-line, user-facing explanation of an autoregulation adjustment.
    None when factor == 1.0 (no adjustment made)."""
    if factor == 1.0:
        return None
    if factor < 1.0:
        pct = round((1.0 - factor) * 100)
        return f"Recent sessions ran harder than planned — load reduced {pct}%"
    pct = round((factor - 1.0) * 100)
    return f"Recent sessions had room to spare — load increased {pct}%"
```

Does not change `compute_adjustment`'s existing signature or return value — `test_autoregulation.py` is unaffected.

### `backend/app/services/progression/deload.py`
Add a pure function alongside `compute_deload_trigger`:

```python
def describe_reactive_deload() -> str:
    """One-line, user-facing explanation shown when a reactive deload fires."""
    return "Readiness has been low recently — built in a lighter week"
```

Static copy (no parameters) is intentional: the *why* (low readiness) is always the same; the specific dates/counts already live in the technical `reason` string used for traceability, not surfaced to the user. Does not change `compute_deload_trigger`'s signature — `test_deload.py` unaffected.

### `backend/app/services/program/preview.py`
- Line 120: capture `reactive_deload_reason` instead of discarding it; compute `deload_reason = describe_reactive_deload() if reactive_deload_triggered else None` once per `derive_week` call.
- Line 144: capture the factor's reason via the new `describe_adjustment(autoreg_factor)` (not the raw technical reason) as `adjustment_reason`, computed per-slot alongside `autoreg_factor`.
- Slot dict (line ~172): add `"adjustment_reason": adjustment_reason`.
- Workout-day dict (line ~183 `days.append(...)`): add `"reactive_deload": reactive_deload_triggered, "deload_reason": deload_reason`.

### `backend/app/schemas/program_api.py`
- `SlotPreviewOut`: add `adjustment_reason: str | None = None`.
- `WorkoutPreviewOut`: add `reactive_deload: bool = False`, `deload_reason: str | None = None`.

## Frontend Changes

### `frontend/src/types/program.ts`
Mirror the three new fields on `SlotPreview` and `WorkoutPreview`.

### `frontend/src/utils/slotNote.ts`
Extend `NOTE_LABELS` with friendly labels for the two tags that currently render raw:
```ts
autoregulated: 'Load adjusted',
reactive_deload: 'Deload week',
```
(`reactive_deload` maps to the same copy as the existing scheduled `deload` label — from the user's perspective both are "a deload week"; the *reason* text is what differentiates them.)

### `frontend/src/pages/WorkoutTrackingPage.tsx`
- **Banner:** near the top of the main content (below the sticky header, above the `SetLogger` card), render:
  ```tsx
  {workoutDetails.reactive_deload && !deloadBannerDismissed && (
    <Alert type="info" dismissible onDismiss={() => setDeloadBannerDismissed(true)} className="mb-4">
      {workoutDetails.deload_reason}
    </Alert>
  )}
  ```
  `deloadBannerDismissed` is local `useState(false)`, declared alongside the existing `toast`/`readinessOpen` state. It naturally resets every time the page mounts (i.e., every workout session), matching the "dismissible, resets next workout" decision — no persistence needed.
- **Per-exercise note section** (lines 299–306): replace the raw `{currentExercise.note}` text with `formatSlotNote(currentExercise.note)` for the label, and add `currentExercise.adjustment_reason` as a descriptive line beneath it when present.
- `ExerciseProgress` interface: add `adjustment_reason: string | null` field, populated from `slot.adjustment_reason` in the `useEffect` that builds `exercises` (line ~77).

## Known pre-existing gap (not in scope)

`_apply_autoregulation` in `preview.py` only sets its own `"autoregulated"` note when no note is already set (`note=scheme.note or "autoregulated"`). If both a reactive deload and an autoregulation adjustment hit the same slot in the same week, the tag stays `"reactive_deload"` and the `"autoregulated"` tag is swallowed. As shipped, `WorkoutTrackingPage.tsx` renders the `adjustment_reason` paragraph nested inside the `{currentExercise.note && (...)}` block, not as an independent sibling — so its visibility is in fact gated on `note` being truthy. In the combined case, `note` stays `"reactive_deload"` (labeled "Deload week") while the `adjustment_reason` text still renders beneath it, so the reason line describing the autoregulation adjustment appears under the deload label. The load math is correct either way; only the *tag* is swallowed. Left alone per user decision; noted here for visibility.

## Testing Plan

**Backend:**
- `test_autoregulation.py`: add cases for `describe_adjustment` — factor < 1.0, factor > 1.0, factor == 1.0 (returns `None`).
- `test_deload.py`: add a case for `describe_reactive_deload` — returns the fixed string.
- `test_preview.py`: extend `derive_week` fixtures to assert `adjustment_reason` appears on slots when `autoreg_factor != 1.0` and is `None` otherwise; assert `reactive_deload`/`deload_reason` appear on workout dicts when the readiness trigger fires.

**Frontend:**
- `WorkoutTrackingPage.test.tsx`: banner renders when `reactive_deload: true`, disappears on dismiss click, doesn't reappear on re-render without remount; per-exercise note shows friendly label + `adjustment_reason` when present.
- `slotNote.test.ts` (or add cases to existing tests): new label mappings.

**Manual/visual:** none required — `Alert` is an existing, already-themed component; no new markup risk like the SetLogger case.

## Non-Goals

- No changes to `compute_adjustment`/`compute_deload_trigger` signatures or their existing technical `reason` strings (still used for internal traceability/debugging).
- No fix for the `note`-overwrite quirk described above.
- No modal, "why" drill-down, or historical adjustment log — spec explicitly asks for a one-line reason only.
