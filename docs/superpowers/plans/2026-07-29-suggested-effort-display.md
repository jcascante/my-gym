# Suggested Effort Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a program's suggested effort (RPE/RIR/Borg/%1RM) always resolve for its slots, and surface it as a visible qualifier next to the sets×reps×load prescription in the plan preview and tracking UI — without changing how the compact `sets x reps @load` string behaves today.

**Architecture:** Two independent, sequential changes. (1) Backend: `preview.py`'s `_effort_target` currently returns `None` whenever the program's stored effort method is `null`; it will default to `"rpe"` instead, so every slot with a `target_rpe` gets a target. (2) Frontend: a new `formatEffortSuffix` helper renders the effort target as a standalone string (`RPE 8`, `RIR 2`, `Borg 18`, `80% 1RM`) whenever a target exists and a load is also present — i.e. exactly the case `formatEffortDisplay` currently drops. Three presentational components render that suffix next to their existing detail line.

**Tech Stack:** FastAPI/Python backend (pytest, `docker-compose exec backend uv run pytest`), React/TypeScript frontend (Vitest, `npm test` from `frontend/`).

## Global Constraints

- TDD: write the failing test before the implementation, for every step below (per `CLAUDE.md`).
- `formatEffortDisplay`'s existing behavior and all of its current call sites are unchanged — this plan only adds a sibling function and new render lines.
- The reporting side (`WorkoutSetLog.effort_method`, `autoregulation._to_rpe_scale`, the `SetRow` effort input) is out of scope. Do not touch `backend/app/services/progression/autoregulation.py`, `backend/app/crud/logging.py`, or `frontend/src/components/SetRow.tsx`.
- No changes to `program.constraints` storage, the program wizard, or any migration — the null-method fallback is applied only at week-derivation time.
- Commit after each task.

---

### Task 1: Backend — null effort method defaults to RPE

**Files:**
- Modify: `backend/app/services/program/preview.py:36-49` (`_effort_target`)
- Test: `backend/tests/test_preview.py:226-250` (`test_derive_week_omits_effort_target_when_effort_method_unset`)

**Interfaces:**
- Consumes: nothing new — `_effort_target(scheme: SetScheme, target_rpe: float | None, intensity_pct: float | None, effort_method: str | None) -> dict[str, Any] | None`, called from `derive_week` at `preview.py:187` as `_effort_target(scheme, ex.target_rpe, ex.intensity_pct, effort_method)` where `effort_method = program.constraints.get("effort_method")` (`preview.py:114`).
- Produces: same signature and return shape, only the `None`-method branch changes.

- [ ] **Step 1: Rewrite the now-contradicted test to expect an RPE fallback**

Replace the test at `backend/tests/test_preview.py:226-250`:

```python
@pytest.mark.asyncio
async def test_derive_week_defaults_effort_target_to_rpe_when_effort_method_unset(
    sample_template_orm, sample_exercises
):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    slots = [s for d in week1 for s in d["slots"]]
    assert slots
    assert all(s["effort_target"] is not None for s in slots)
    assert all(s["effort_target"]["method"] == "rpe" for s in slots)
```

**Do not** rename the old test and keep both — the old name and assertion (`all(s["effort_target"] is None ...)`) directly contradict the new behavior, so it must be replaced, not duplicated.

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker-compose exec -T backend uv run pytest tests/test_preview.py::test_derive_week_defaults_effort_target_to_rpe_when_effort_method_unset -v`
Expected: FAIL — every slot's `effort_target` is currently `None`.

- [ ] **Step 3: Update `_effort_target` to default a null method to RPE**

In `backend/app/services/program/preview.py`, replace:

```python
def _effort_target(
    scheme: SetScheme, target_rpe: float | None, intensity_pct: float | None, effort_method: str | None
) -> dict[str, Any] | None:
    if effort_method is None or target_rpe is None:
        return None
    if effort_method == "rpe":
        return {"method": "rpe", "value": target_rpe}
    if effort_method == "rir":
        return {"method": "rir", "value": round(10 - target_rpe)}
    if effort_method == "borg":
        return {"method": "borg", "value": min(20, max(6, round(target_rpe * 2 + 2)))}
    if effort_method == "percent_1rm" and intensity_pct is not None:
        return {"method": "percent_1rm", "pct": intensity_pct, "target_load": scheme.load}
    return None
```

with:

```python
def _effort_target(
    scheme: SetScheme, target_rpe: float | None, intensity_pct: float | None, effort_method: str | None
) -> dict[str, Any] | None:
    if target_rpe is None:
        return None
    method = effort_method or "rpe"
    if method == "rpe":
        return {"method": "rpe", "value": target_rpe}
    if method == "rir":
        return {"method": "rir", "value": round(10 - target_rpe)}
    if method == "borg":
        return {"method": "borg", "value": min(20, max(6, round(target_rpe * 2 + 2)))}
    if method == "percent_1rm" and intensity_pct is not None:
        return {"method": "percent_1rm", "pct": intensity_pct, "target_load": scheme.load}
    return None
```

- [ ] **Step 4: Run the full preview test file to verify the new test passes and nothing else broke**

Run: `docker-compose exec -T backend uv run pytest tests/test_preview.py -v`
Expected: all tests PASS, including `test_derive_week_defaults_effort_target_to_rpe_when_effort_method_unset`, `test_derive_week_includes_rpe_effort_target_when_requested`, `test_derive_week_converts_rpe_to_rir`, and `test_derive_week_percent_1rm_target_includes_load`.

- [ ] **Step 5: Run the broader backend suite for regressions**

Run: `docker-compose exec -T backend uv run pytest tests/test_effort_method.py tests/test_scheduling.py tests/test_drafting.py tests/services/progression/test_autoregulation.py -v`
Expected: all PASS — these exercise adjacent code (`_base_load_for`, autoregulation) that reads `effort_method` too but was not modified.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/program/preview.py backend/tests/test_preview.py
git commit -m "fix: default program effort method to RPE when unset"
```

---

### Task 2: Frontend — `formatEffortSuffix` utility

**Files:**
- Modify: `frontend/src/utils/effortDisplay.ts`
- Test: `frontend/src/utils/__tests__/effortDisplay.test.ts`

**Interfaces:**
- Consumes: `EffortTarget` from `@/types/program` (`{ method: 'rpe' | 'rir' | 'borg' | 'percent_1rm'; value?: number; pct?: number; target_load?: number | null }`), already imported in `effortDisplay.ts`.
- Produces: `formatEffortSuffix(load: number | null, effortTarget: EffortTarget | null): string | null`, consumed by Task 3 and Task 4.

- [ ] **Step 1: Write the failing tests**

Append to `frontend/src/utils/__tests__/effortDisplay.test.ts` (new `describe` block, same file, after the existing `formatEffortDisplay` block):

```ts
describe('formatEffortSuffix', () => {
  it('returns null when there is no effort target', () => {
    expect(formatEffortSuffix(80, null)).toBeNull();
  });

  it('returns null when there is no load, even with an effort target', () => {
    const effortTarget: EffortTarget = { method: 'rpe', value: 8 };
    expect(formatEffortSuffix(null, effortTarget)).toBeNull();
  });

  it('formats an RPE suffix when both load and target are present', () => {
    const effortTarget: EffortTarget = { method: 'rpe', value: 8 };
    expect(formatEffortSuffix(80, effortTarget)).toBe('RPE 8');
  });

  it('formats an RIR suffix', () => {
    const effortTarget: EffortTarget = { method: 'rir', value: 2 };
    expect(formatEffortSuffix(80, effortTarget)).toBe('RIR 2');
  });

  it('formats a Borg suffix', () => {
    const effortTarget: EffortTarget = { method: 'borg', value: 18 };
    expect(formatEffortSuffix(80, effortTarget)).toBe('Borg 18');
  });

  it('formats a percent_1rm suffix as a rounded percentage with the 1RM label', () => {
    const effortTarget: EffortTarget = { method: 'percent_1rm', pct: 0.8, target_load: 80 };
    expect(formatEffortSuffix(80, effortTarget)).toBe('80% 1RM');
  });
});
```

Also update the existing `percent_1rm` test in the `formatEffortDisplay` block (same file, line 16-20) to the new wording:

```ts
  it('formats percent_1rm effort when no weight', () => {
    const effortTarget: EffortTarget = { method: 'percent_1rm', pct: 0.7 };
    const result = formatEffortDisplay(4, 10, null, 'lbs', effortTarget);
    expect(result).toBe('4 x 10 @70% 1RM');
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- effortDisplay.test.ts`
Expected: FAIL — `formatEffortSuffix` is not exported/defined yet, and the updated `percent_1rm` expectation (`@70% 1RM`) doesn't match the current `@70%` output.

- [ ] **Step 3: Implement `formatEffortSuffix` and update the shared label mapping**

Replace the full contents of `frontend/src/utils/effortDisplay.ts` with:

```ts
import type { WeightUnit } from '@/types/programCreation';
import type { EffortTarget } from '@/types/program';

function effortLabel(effortTarget: EffortTarget): string {
  switch (effortTarget.method) {
    case 'percent_1rm':
      return `${Math.round((effortTarget.pct ?? 0) * 100)}% 1RM`;
    case 'rir':
      return `RIR ${effortTarget.value}`;
    case 'rpe':
      return `RPE ${effortTarget.value}`;
    case 'borg':
      return `Borg ${effortTarget.value}`;
  }
}

export function formatEffortDisplay(
  sets: number,
  reps: number,
  load: number | null,
  weightUnit: WeightUnit,
  effortTarget: EffortTarget | null,
): string {
  const baseFormat = `${sets} x ${reps}`;

  // Weight-based effort is preferred
  if (load !== null) {
    return `${baseFormat} @${load} ${weightUnit}`;
  }

  // Fall back to effort target if no weight
  if (effortTarget) {
    return `${baseFormat} @${effortLabel(effortTarget)}`;
  }

  // Fallback to just sets x reps
  return baseFormat;
}

// The counterpart to formatEffortDisplay's precedence rule: when a load is present,
// formatEffortDisplay's output already carries the weight and drops the effort target
// entirely. This renders that dropped target as a standalone qualifier instead of
// folding it back into the same string, so a loaded slot can show both.
export function formatEffortSuffix(
  load: number | null,
  effortTarget: EffortTarget | null,
): string | null {
  if (load === null || !effortTarget) {
    return null;
  }
  return effortLabel(effortTarget);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- effortDisplay.test.ts`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/effortDisplay.ts frontend/src/utils/__tests__/effortDisplay.test.ts
git commit -m "feat: add formatEffortSuffix for loaded-slot effort targets"
```

---

### Task 3: Frontend — render the suffix in tracking (`ExerciseSection`)

**Files:**
- Modify: `frontend/src/components/ExerciseSection.tsx`
- Test: `frontend/src/components/ExerciseSection.test.tsx`

**Interfaces:**
- Consumes: `formatEffortSuffix(load: number | null, effortTarget: EffortTarget | null): string | null` from Task 2 (`@/utils/effortDisplay`, imported here as `../utils/effortDisplay` matching this file's existing import style).
- Produces: no new exports; visual change only.

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/components/ExerciseSection.test.tsx`, inside the `describe('ExerciseSection', ...)` block:

```tsx
  it('shows the effort suffix on the Target line when a load and effort target are both present', () => {
    render(
      <ExerciseSection
        exercise={exercise({ load: 80, effort_target: { method: 'rpe', value: 8 } })}
        effort_method="rpe"
        weightUnit="lbs"
        isOpen
        onToggle={vi.fn()}
        onLogSet={vi.fn()}
      />,
    );

    expect(screen.getByText('Target: 2 x 8 @80 lbs · RPE 8 · Rest 1:30')).toBeInTheDocument();
  });

  it('does not show the effort suffix in the collapsed header even with a load and effort target', () => {
    render(
      <ExerciseSection
        exercise={exercise({ load: 80, effort_target: { method: 'rpe', value: 8 } })}
        effort_method="rpe"
        weightUnit="lbs"
        isOpen={false}
        onToggle={vi.fn()}
        onLogSet={vi.fn()}
      />,
    );

    expect(screen.getByText('2 x 8 @80 lbs')).toBeInTheDocument();
    expect(screen.queryByText(/RPE 8/)).not.toBeInTheDocument();
  });
```

(`rest_seconds: 90` from the shared `exercise()` fixture is why the expected string reads `Rest 1:30`, matching the existing `Target:` line's minute:second formatting at `ExerciseSection.tsx:69-70`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- ExerciseSection.test.tsx`
Expected: FAIL — the `Target:` line currently renders `Target: 2 x 8 @80 lbs · Rest 1:30`, with no `RPE 8`.

- [ ] **Step 3: Implement**

In `frontend/src/components/ExerciseSection.tsx`, update the import and add the suffix:

```tsx
import { formatEffortDisplay, formatEffortSuffix } from '../utils/effortDisplay';
```

```tsx
  const effortDisplay = formatEffortDisplay(
    exercise.sets,
    exercise.reps,
    exercise.load,
    weightUnit,
    exercise.effort_target,
  );
  const effortSuffix = formatEffortSuffix(exercise.load, exercise.effort_target);
```

Replace the `Target:` line:

```tsx
            <span>
              Target: {effortDisplay}
              {effortSuffix ? ` · ${effortSuffix}` : ''} · Rest {Math.floor(exercise.rest_seconds / 60)}:
              {String(exercise.rest_seconds % 60).padStart(2, '0')}
            </span>
```

The collapsed header's `{effortDisplay}` span (line 56-58) is unchanged — it never renders `effortSuffix`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- ExerciseSection.test.tsx`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ExerciseSection.tsx frontend/src/components/ExerciseSection.test.tsx
git commit -m "feat: show suggested effort next to loaded sets in exercise target line"
```

---

### Task 4: Frontend — render the suffix chip in plan preview (`SlotRow`, `ExerciseSlotCard`)

**Files:**
- Modify: `frontend/src/components/SlotRow.tsx`
- Modify: `frontend/src/components/ExerciseSlotCard.tsx`
- Test: `frontend/src/tests/components/SlotRow.test.tsx`
- Test: `frontend/src/tests/components/ExerciseSlotCard.test.tsx`

**Interfaces:**
- Consumes: `formatEffortSuffix(load: number | null, effortTarget: EffortTarget | null): string | null` from Task 2 (`@/utils/effortDisplay`, matching both files' existing import path).
- Produces: no new exports; visual change only.

- [ ] **Step 1: Write the failing tests**

Add to `frontend/src/tests/components/SlotRow.test.tsx`, inside `describe('SlotRow', ...)`:

```tsx
  it('shows an effort suffix chip when load and effort_target are both present', () => {
    const slot = {
      ...baseSlot,
      load: 100,
      effort_target: { method: 'rpe' as const, value: 8 },
    };
    render(<SlotRow slot={slot} weightUnit="kg" onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.getByText('3 x 5 @100 kg')).toBeInTheDocument();
    expect(screen.getByText('RPE 8')).toBeInTheDocument();
  });

  it('does not show an effort suffix chip when load is present but effort_target is null', () => {
    render(<SlotRow slot={baseSlot} weightUnit="kg" onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.queryByText(/RPE|RIR|Borg|%/)).not.toBeInTheDocument();
  });
```

Add to `frontend/src/tests/components/ExerciseSlotCard.test.tsx`, inside `describe('integration', ...)`:

```tsx
    it('shows an effort suffix chip when load and effort_target are both present', () => {
      const slot = {
        ...baseSlot,
        load: 100,
        effort_target: { method: 'rir' as const, value: 2 },
      };
      render(wrap(<ExerciseSlotCard slot={slot} programId={1} weightUnit="lbs" readOnly />));
      expect(screen.getByText(/3 x 5 @100 lbs/)).toBeInTheDocument();
      expect(screen.getByText('RIR 2')).toBeInTheDocument();
    });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- SlotRow.test.tsx ExerciseSlotCard.test.tsx`
Expected: FAIL — neither `RPE 8` nor `RIR 2` render today.

- [ ] **Step 3: Implement in `SlotRow.tsx`**

Update the import:

```tsx
import { formatEffortDisplay, formatEffortSuffix } from '@/utils/effortDisplay';
```

Add the suffix computation alongside `effortDisplay`:

```tsx
  const effortDisplay = formatEffortDisplay(
    slot.sets,
    slot.reps,
    slot.load,
    weightUnit,
    slot.effort_target,
  );
  const effortSuffix = formatEffortSuffix(slot.load, slot.effort_target);
```

Add a chip next to the existing `effortDisplay` span (inside the `flex flex-wrap gap-2 mt-1` div, before the `note` chip):

```tsx
            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
              {effortDisplay}
            </span>
            {effortSuffix && (
              <span className="text-sm text-neutral-500 dark:text-neutral-400">
                {effortSuffix}
              </span>
            )}
```

- [ ] **Step 4: Implement in `ExerciseSlotCard.tsx`**

Update the import:

```tsx
import { formatEffortDisplay, formatEffortSuffix } from '@/utils/effortDisplay';
```

Add the suffix computation alongside `effortDisplay`:

```tsx
  const effortDisplay = formatEffortDisplay(
    slot.sets,
    slot.reps,
    slot.load,
    weightUnit,
    slot.effort_target,
  );
  const effortSuffix = formatEffortSuffix(slot.load, slot.effort_target);
```

Add a chip next to the existing `effortDisplay` span (inside the `flex flex-wrap gap-1 mt-0.5` div, before the `Rest:` chip):

```tsx
          <span className="text-xs font-medium text-neutral-700 dark:text-neutral-300">
            {effortDisplay}
          </span>
          {effortSuffix && (
            <span className="text-xs text-neutral-500 dark:text-neutral-400">
              {effortSuffix}
            </span>
          )}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npm test -- SlotRow.test.tsx ExerciseSlotCard.test.tsx`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/SlotRow.tsx frontend/src/components/ExerciseSlotCard.tsx frontend/src/tests/components/SlotRow.test.tsx frontend/src/tests/components/ExerciseSlotCard.test.tsx
git commit -m "feat: show suggested effort chip for loaded slots in plan preview"
```

---

### Task 5: Full regression pass

**Files:** none (verification only)

**Interfaces:** none

- [ ] **Step 1: Run the full backend suite**

Run: `docker-compose exec -T backend uv run pytest`
Expected: all PASS, no new failures.

- [ ] **Step 2: Run the full frontend suite**

Run: `cd frontend && npm test -- --run`
Expected: all PASS, no new failures.

- [ ] **Step 3: Manually verify in the running app**

With `docker-compose up` already running (per `CLAUDE.md`'s quick-start), open a workout tracking session for a program whose `effort_method` is unset (drafted via the wizard's "Not sure yet / skip" option) and confirm:
- A loadless accessory slot's header reads e.g. `3 x 12 @ RPE 7` (unchanged from before).
- A loaded main-lift slot's collapsed header still reads e.g. `4 x 5 @80 kg` with no RPE.
- Expanding that same main-lift slot shows `Target: 4 x 5 @80 kg · RPE 8 · Rest 2:00`.
- The program preview page (`SlotRow`/`ExerciseSlotCard`) shows the same `RPE 8`-style chip next to loaded main lifts.

No `docker-compose restart` needed — both dev servers hot-reload.
