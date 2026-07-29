# Enhanced Load Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display effort/intensity consistently across exercise scheduling and tracking views using the format `sets × reps @load` (weight-based) or `sets × reps @effort_method value` (effort-based fallback).

**Architecture:** Create a reusable `formatEffortDisplay()` utility that formats the effort string based on weight availability (preferred) or effort target. Thread `weight_unit` through ExerciseSection and SetRow components as props. Update display surfaces in ExerciseSection header/details and SetRow summary mode.

**Tech Stack:** React, TypeScript, Tailwind (existing); types from `@/types/programCreation` and `@/types/program`

## Global Constraints

- Weight unit comes from `userProfile.weight_unit` (WeightUnit: 'kg' | 'lbs')
- EffortTarget type: `{ method: 'rpe'|'rir'|'borg'|'percent_1rm', value?: number, pct?: number, target_load?: number|null }`
- Format: `sets x reps @effort` (e.g., `4 x 10 @80 lbs`, `4 x 10 @RIR 1`, `4 x 10 @70%`)
- Display in: ExerciseSection (header + details), SetRow (summary mode)

---

### Task 1: Create formatEffortDisplay Utility & Tests

**Files:**
- Create: `frontend/src/utils/effortDisplay.ts`
- Create: `frontend/src/utils/__tests__/effortDisplay.test.ts`

**Interfaces:**
- Produces: `formatEffortDisplay(sets: number, reps: number, load: number | null, weightUnit: WeightUnit, effortTarget: EffortTarget | null): string`

- [ ] **Step 1: Write test file with all effort scenarios**

Create `frontend/src/utils/__tests__/effortDisplay.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { formatEffortDisplay } from '../effortDisplay';
import type { WeightUnit } from '@/types/programCreation';
import type { EffortTarget } from '@/types/program';

describe('formatEffortDisplay', () => {
  it('formats weight-based effort (lbs)', () => {
    const result = formatEffortDisplay(4, 10, 80, 'lbs', null);
    expect(result).toBe('4 x 10 @80 lbs');
  });

  it('formats weight-based effort (kg)', () => {
    const result = formatEffortDisplay(4, 10, 80, 'kg', null);
    expect(result).toBe('4 x 10 @80 kg');
  });

  it('formats percent_1rm effort when no weight', () => {
    const effortTarget: EffortTarget = { method: 'percent_1rm', pct: 70 };
    const result = formatEffortDisplay(4, 10, null, 'lbs', effortTarget);
    expect(result).toBe('4 x 10 @70%');
  });

  it('formats RIR effort when no weight', () => {
    const effortTarget: EffortTarget = { method: 'rir', value: 1 };
    const result = formatEffortDisplay(4, 10, null, 'lbs', effortTarget);
    expect(result).toBe('4 x 10 @RIR 1');
  });

  it('formats RPE effort when no weight', () => {
    const effortTarget: EffortTarget = { method: 'rpe', value: 7 };
    const result = formatEffortDisplay(4, 10, null, 'lbs', effortTarget);
    expect(result).toBe('4 x 10 @RPE 7');
  });

  it('formats Borg effort when no weight', () => {
    const effortTarget: EffortTarget = { method: 'borg', value: 12 };
    const result = formatEffortDisplay(4, 10, null, 'lbs', effortTarget);
    expect(result).toBe('4 x 10 @Borg 12');
  });

  it('prefers weight over effort_target when both available', () => {
    const effortTarget: EffortTarget = { method: 'rpe', value: 7 };
    const result = formatEffortDisplay(4, 10, 80, 'lbs', effortTarget);
    expect(result).toBe('4 x 10 @80 lbs');
  });

  it('returns sets x reps only when no weight and no effort_target', () => {
    const result = formatEffortDisplay(4, 10, null, 'lbs', null);
    expect(result).toBe('4 x 10');
  });

  it('handles decimal weight values', () => {
    const result = formatEffortDisplay(4, 10, 80.5, 'lbs', null);
    expect(result).toBe('4 x 10 @80.5 lbs');
  });
});
```

- [ ] **Step 2: Run tests to verify all fail**

```bash
cd /Users/jorgecascante/develop/my-gym
npm test -- frontend/src/utils/__tests__/effortDisplay.test.ts
```

Expected: All 8 tests fail with "formatEffortDisplay not defined"

- [ ] **Step 3: Implement formatEffortDisplay utility**

Create `frontend/src/utils/effortDisplay.ts`:

```typescript
import type { WeightUnit } from '@/types/programCreation';
import type { EffortTarget } from '@/types/program';

export function formatEffortDisplay(
  sets: number,
  reps: number,
  load: number | null,
  weightUnit: WeightUnit,
  effortTarget: EffortTarget | null,
): string {
  const baseFormat = `${sets} x ${reps}`;

  // Prefer weight-based display
  if (load !== null) {
    return `${baseFormat} @${load} ${weightUnit}`;
  }

  // Fall back to effort target
  if (effortTarget) {
    const { method, value, pct } = effortTarget;

    switch (method) {
      case 'percent_1rm':
        return `${baseFormat} @${pct}%`;
      case 'rir':
        return `${baseFormat} @RIR ${value}`;
      case 'rpe':
        return `${baseFormat} @RPE ${value}`;
      case 'borg':
        return `${baseFormat} @Borg ${value}`;
      default:
        return baseFormat;
    }
  }

  return baseFormat;
}
```

- [ ] **Step 4: Run tests to verify all pass**

```bash
npm test -- frontend/src/utils/__tests__/effortDisplay.test.ts
```

Expected: All 8 tests pass

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/effortDisplay.ts frontend/src/utils/__tests__/effortDisplay.test.ts
git commit -m "feat: add formatEffortDisplay utility for consistent effort display"
```

---

### Task 2: Update ExerciseSection Component

**Files:**
- Modify: `frontend/src/components/ExerciseSection.tsx`
- Modify: `frontend/src/components/ExerciseSection.test.tsx`

**Interfaces:**
- Consumes: `formatEffortDisplay(sets, reps, load, weightUnit, effortTarget): string` from Task 1
- Produces: ExerciseSection now accepts `weightUnit: WeightUnit` prop (required)

- [ ] **Step 1: Update ExerciseSection tests to add weightUnit prop**

In `frontend/src/components/ExerciseSection.test.tsx`, update all render calls to include the prop:

```typescript
// Around line 30-42 (showsTheSetCount test)
render(
  <ExerciseSection
    exercise={exercise()}
    effort_method="rpe"
    weightUnit="lbs"
    isOpen={false}
    onToggle={vi.fn()}
    onLogSet={vi.fn()}
  />,
);

// Repeat for all other render() calls in the test file (showsACheckmark, callsOnToggle, rendersOneSetRow)
// Update the exercise() mock to include effort_target if needed:
const exercise = (overrides: Partial<ExerciseProgress> = {}): ExerciseProgress => ({
  // ... existing fields ...
  effort_target: null,  // Add this line
  ...overrides,
});
```

- [ ] **Step 2: Run tests to verify they fail (missing weightUnit prop)**

```bash
npm test -- frontend/src/components/ExerciseSection.test.tsx
```

Expected: Tests fail with "Property 'weightUnit' is missing in type"

- [ ] **Step 3: Update ExerciseSection component signature and header display**

In `frontend/src/components/ExerciseSection.tsx`:

```typescript
import React from 'react';
import { EffortMethod } from '../types/programCreation';
import type { WeightUnit } from '../types/programCreation';
import { SetRow } from './SetRow';
import { formatSlotNote } from '../utils/slotNote';
import { formatEffortDisplay } from '../utils/effortDisplay';
import type { ExerciseProgress, LoggedSetEntry } from '../hooks/useSessionProgress';

interface ExerciseSectionProps {
  exercise: ExerciseProgress;
  effort_method: EffortMethod;
  weightUnit: WeightUnit;
  isOpen: boolean;
  onToggle: () => void;
  onLogSet: (
    setNumber: number,
    data: { weight?: number; reps?: number; effort: number; effort_method: EffortMethod },
  ) => Promise<void> | void;
}

export const ExerciseSection: React.FC<ExerciseSectionProps> = ({
  exercise,
  effort_method,
  weightUnit,
  isOpen,
  onToggle,
  onLogSet,
}) => {
  const completedCount = exercise.completedSets.length;
  const isComplete = completedCount >= exercise.sets;
  const findSet = (setNumber: number): LoggedSetEntry | undefined =>
    exercise.completedSets.find((s) => s.setNumber === setNumber);

  const effortDisplay = formatEffortDisplay(
    exercise.sets,
    exercise.reps,
    exercise.load,
    weightUnit,
    exercise.effort_target,
  );

  return (
    <div
      data-testid={`exercise-section-${exercise.workout_exercise_id}`}
      className="border border-neutral-200 dark:border-neutral-700 rounded-lg mb-3 bg-white dark:bg-neutral-800 overflow-hidden"
    >
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        className="w-full flex items-center justify-between px-4 py-3"
      >
        <span className="flex items-center gap-2 font-semibold text-neutral-900 dark:text-neutral-100">
          {isComplete && <span className="text-success-600 dark:text-success-400">✓</span>}
          {exercise.exercise_name}
        </span>
        <span className="flex items-center gap-3 text-xs text-neutral-600 dark:text-neutral-400">
          <span>{effortDisplay}</span>
          <span>{completedCount}/{exercise.sets} sets</span>
          <span>{isOpen ? '▴' : '▾'}</span>
        </span>
      </button>

      {isOpen && (
        <div className="px-4 pb-4 space-y-3">
          <div className="text-xs text-neutral-600 dark:text-neutral-400">
            <span>
              Target: {effortDisplay} · Rest {Math.floor(exercise.rest_seconds / 60)}:
              {String(exercise.rest_seconds % 60).padStart(2, '0')}
            </span>
          </div>

          {exercise.note && (
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              {formatSlotNote(exercise.note)}
              {exercise.adjustment_reason ? ` — ${exercise.adjustment_reason}` : ''}
            </p>
          )}

          <div className="space-y-2">
            {Array.from({ length: exercise.sets }, (_, i) => i + 1).map((setNumber) => (
              <SetRow
                key={setNumber}
                setNumber={setNumber}
                effort_method={effort_method}
                weightUnit={weightUnit}
                loggedSet={findSet(setNumber)}
                idPrefix={exercise.workout_exercise_id}
                onLogSet={(data) => onLogSet(setNumber, data)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- frontend/src/components/ExerciseSection.test.tsx
```

Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ExerciseSection.tsx frontend/src/components/ExerciseSection.test.tsx
git commit -m "feat: display effort in ExerciseSection header and details using formatEffortDisplay"
```

---

### Task 3: Update SetRow Component

**Files:**
- Modify: `frontend/src/components/SetRow.tsx`
- Modify: `frontend/src/components/SetRow.test.tsx` (if exists; if not, minimal changes)

**Interfaces:**
- Consumes: `formatEffortDisplay(sets, reps, load, weightUnit, effortTarget): string` from Task 1
- Produces: SetRow now accepts `weightUnit: WeightUnit` prop (required)

- [ ] **Step 1: Update SetRow component signature**

In `frontend/src/components/SetRow.tsx`, add the import and prop:

```typescript
import type { WeightUnit } from '../types/programCreation';
import { formatEffortDisplay } from '../utils/effortDisplay';

interface SetRowProps {
  setNumber: number;
  effort_method: EffortMethod;
  weightUnit: WeightUnit;
  loggedSet?: LoggedSetEntry;
  idPrefix?: string | number;
  onLogSet: (data: {
    weight?: number;
    reps?: number;
    effort: number;
    effort_method: EffortMethod;
  }) => Promise<void> | void;
}

export const SetRow: React.FC<SetRowProps> = ({
  setNumber,
  effort_method,
  weightUnit,
  loggedSet,
  idPrefix,
  onLogSet,
}) => {
  // ... existing code ...
}
```

- [ ] **Step 2: Update SetRow summary mode display**

Replace the summary mode return (around line 105-121) with:

```typescript
if (mode === 'summary' && loggedSet) {
  const performedDisplay = formatEffortDisplay(
    1,  // SetRow shows one set at a time
    loggedSet.reps ?? 0,
    loggedSet.weight ?? null,
    weightUnit,
    loggedSet.effort_method && loggedSet.effort
      ? {
          method: loggedSet.effort_method,
          value: loggedSet.effort,
        }
      : null,
  );

  return (
    <button
      type="button"
      onClick={handleEditTap}
      aria-label={`Set ${setNumber} logged, tap to edit`}
      className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-success-50 dark:bg-success-900 border border-success-200 dark:border-success-700 text-left"
    >
      <span className="text-body-sm font-variant-numeric tabular-nums">
        Set {setNumber} · {performedDisplay}
      </span>
      <span className="text-success-600 dark:text-success-400 text-sm shrink-0">
        ✓ tap to edit
      </span>
    </button>
  );
}
```

- [ ] **Step 3: Run component visually (dev server)**

```bash
npm run dev
```

Navigate to a workout tracking page and verify:
- ExerciseSection header shows effort display (e.g., "4 x 10 @80 lbs")
- ExerciseSection expanded view shows effort in details (e.g., "Target: 4 x 10 @80 lbs")
- SetRow summary (after logging) shows effort (e.g., "Set 1 · 1 x 8 @80 lbs")

- [ ] **Step 4: Run tests**

```bash
npm test -- frontend/src/components/SetRow.test.tsx
```

Expected: Tests pass (or update them if they have hardcoded display assertions)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/SetRow.tsx
git commit -m "feat: display effort in SetRow summary using formatEffortDisplay"
```

---

### Task 4: Update WorkoutTrackingPage to Thread weightUnit

**Files:**
- Modify: `frontend/src/pages/WorkoutTrackingPage.tsx`

**Interfaces:**
- Consumes: `userProfile.weight_unit` (WeightUnit from auth store)
- Produces: ExerciseSection receives weightUnit prop

- [ ] **Step 1: Add weightUnit extraction in WorkoutTrackingPage**

In `frontend/src/pages/WorkoutTrackingPage.tsx`, after the `effortMethod` extraction (around line 22):

```typescript
const { userProfile } = useAuthStore();

const rawEffortMethod = userProfile?.effort_method;
const effortMethod: EffortMethod =
  rawEffortMethod === 'rpe' || rawEffortMethod === 'rir' || rawEffortMethod === 'borg'
    ? rawEffortMethod
    : 'rpe';

// Add this block:
const weightUnit: WeightUnit = userProfile?.weight_unit ?? 'lbs';
```

You'll also need to add the import:

```typescript
import type { WeightUnit } from '@/types/programCreation';
```

- [ ] **Step 2: Pass weightUnit to ExerciseSection**

Find the ExerciseSection render call (around line 180-190) and add the prop:

```typescript
<ExerciseSection
  exercise={exercise}
  effort_method={effortMethod}
  weightUnit={weightUnit}
  isOpen={openIds.has(exercise.workout_exercise_id)}
  onToggle={() => toggleSection(exercise.workout_exercise_id)}
  onLogSet={(setNumber, data) => handleLogSet(exercise.workout_exercise_id, setNumber, data)}
/>
```

- [ ] **Step 3: Run the app and test**

```bash
npm run dev
```

Navigate to a workout tracking page and verify:
- Weight unit displays correctly (lbs or kg based on user profile)
- Exercises show effort with correct units
- SetRow summary shows correct units after logging

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/WorkoutTrackingPage.tsx
git commit -m "feat: thread weight_unit from userProfile to ExerciseSection and SetRow"
```

---

### Task 5: Verify Effort Display in Schedule View (DraftProgramView)

**Files:**
- Check: `frontend/src/components/DraftProgramView.tsx` (or similar schedule display)
- Modify if needed: `frontend/src/components/DraftProgramView.tsx`

**Interfaces:**
- Consumes: Same formatEffortDisplay utility
- Produces: Schedule view also shows effort display (optional enhancement)

- [ ] **Step 1: Check if schedule view needs weightUnit**

Open `frontend/src/components/DraftProgramView.tsx` and look for where exercises are displayed in the schedule/list view (not the tracking detail view). Check if it shows exercise details like "4 x 10 @80 lbs" or just "4 x 10".

```bash
grep -n "load\|reps\|sets" frontend/src/components/DraftProgramView.tsx | head -20
```

- [ ] **Step 2: If schedule view displays exercises, add weightUnit prop**

If DraftProgramView shows exercises, add `weightUnit` prop similar to Task 4. If it doesn't display detailed exercise info (only exercise names), skip this step.

If you add it, commit:

```bash
git add frontend/src/components/DraftProgramView.tsx
git commit -m "feat: display effort in schedule view using formatEffortDisplay"
```

- [ ] **Step 3: If no changes needed, mark complete**

If the schedule view doesn't show detailed exercise loads/reps, no changes are needed. Mark as complete.

---

### Task 6: Final Integration Test

**Files:**
- Test: Manual testing across scheduling and tracking views

- [ ] **Step 1: Start dev server**

```bash
npm run dev
```

- [ ] **Step 2: Test scenario 1: Weight-based effort**

1. Navigate to a workout with exercises that have `load` values
2. Check ExerciseSection header displays effort (e.g., "4 x 10 @80 lbs")
3. Click to expand, verify details show effort (e.g., "Target: 4 x 10 @80 lbs")
4. Log a set and verify summary shows effort (e.g., "Set 1 · 1 x 8 @80 lbs")

- [ ] **Step 3: Test scenario 2: Effort-target-based (RPE/RIR/Borg/Percent)**

1. If available, navigate to a workout with exercises that have NO `load` but have `effort_target`
2. Verify ExerciseSection displays effort (e.g., "4 x 10 @RPE 7" or "4 x 10 @RIR 2")
3. Expand and verify details show correct format
4. Log a set and verify summary shows effort correctly

- [ ] **Step 4: Test scenario 3: Weight units (kg vs lbs)**

1. If your test user has `weight_unit: 'kg'`, verify displays show "kg" instead of "lbs"
2. Check both header, details, and SetRow summary

- [ ] **Step 5: Test scenario 4: No load, no effort_target**

1. If any exercise has neither load nor effort_target, verify it displays "4 x 10" (no @)

- [ ] **Step 6: Run full test suite**

```bash
npm test
```

Expected: All tests pass, no regressions in other components

- [ ] **Step 7: Commit if any manual-test fixes were needed**

```bash
git add .
git commit -m "fix: resolve manual testing issues with effort display"
```

---

## Spec Coverage Check

✅ **Weight-based display (e.g., `4 x 10 @80 lbs`)** — Task 1 (utility), Tasks 2–4 (components)
✅ **Effort-target display (e.g., `4 x 10 @RPE 6`)** — Task 1 (utility handles all methods)
✅ **Weight unit display (kg/lbs)** — Task 4 (threads from userProfile)
✅ **ExerciseSection header (collapsed)** — Task 2 (added to button area)
✅ **ExerciseSection details (expanded)** — Task 2 (added to "Target:" line)
✅ **SetRow summary** — Task 3 (after logging)
✅ **Schedule view** — Task 5 (if applicable)
